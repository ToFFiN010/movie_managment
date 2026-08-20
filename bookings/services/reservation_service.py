import logging
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from bookings.models import ShowSchedule, Seat, ShowSeat, Reservation, ReservationSeat, Booking

logger = logging.getLogger(__name__)

CONVENIENCE_FEE_PER_TICKET = Decimal('2.50')


def broadcast_seat_update(show_id, seat_ids, status, user_id=None):
    """
    Broadcast seat availability state changes over Django Channels WebSocket.
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"show_{show_id}",
                {
                    "type": "seat_update",
                    "seat_ids": seat_ids,
                    "status": status,
                    "user_id": user_id,
                    "timestamp": timezone.now().isoformat()
                }
            )
    except Exception as e:
        logger.warning(f"WebSocket broadcast skipped or failed: {e}")


def release_expired_reservations_for_show(show_id=None):
    """
    Find and expire all stale active reservations where expires_at <= now.
    """
    now = timezone.now()
    qs = Reservation.objects.filter(status=Reservation.Status.ACTIVE, expires_at__lte=now)
    if show_id:
        qs = qs.filter(show_id=show_id)

    expired_count = 0
    for res in qs.select_related('show').prefetch_related('reserved_seats'):
        with transaction.atomic():
            res.status = Reservation.Status.EXPIRED
            res.save(update_fields=['status'])
            
            seat_ids = list(res.reserved_seats.values_list('seat_id', flat=True))
            # Mark ShowSeats as AVAILABLE unless already booked
            ShowSeat.objects.filter(
                show=res.show,
                seat_id__in=seat_ids
            ).exclude(status=ShowSeat.Status.BOOKED).update(status=ShowSeat.Status.AVAILABLE)

            broadcast_seat_update(res.show_id, seat_ids, ShowSeat.Status.AVAILABLE)
            expired_count += 1

    return expired_count


class ReservationService:
    @staticmethod
    def hold_seats(user, show_id, seat_ids):
        """
        Atomically reserve seats for 2 minutes using transaction.atomic() & select_for_update().
        """
        if not seat_ids:
            raise ValueError("No seats specified for reservation.")

        # Clean up any expired reservations first
        release_expired_reservations_for_show(show_id)

        with transaction.atomic():
            show = ShowSchedule.objects.select_for_update().get(id=show_id)

            # Ensure all requested seats exist for screen
            seats = list(Seat.objects.filter(id__in=seat_ids, screen=show.screen, is_active=True))
            if len(seats) != len(seat_ids):
                raise ValueError("One or more selected seats are invalid or inactive.")

            # Lock ShowSeats for these seats
            existing_ss_seat_ids = set(ShowSeat.objects.filter(show=show, seat_id__in=seat_ids).values_list('seat_id', flat=True))
            missing_ids = set(seat_ids) - existing_ss_seat_ids
            if missing_ids:
                ShowSeat.objects.bulk_create([
                    ShowSeat(show=show, seat_id=sid, status=ShowSeat.Status.AVAILABLE) for sid in missing_ids
                ], ignore_conflicts=True)

            show_seats = list(ShowSeat.objects.select_for_update().filter(show=show, seat_id__in=seat_ids))
            
            # Check if any seat is already BOOKED
            for ss in show_seats:
                if ss.status == ShowSeat.Status.BOOKED:
                    raise ValueError(f"Seat {ss.seat.label} is already booked.")

            # Check for active reservations held by OTHER users
            now = timezone.now()
            active_other_res_seats = ReservationSeat.objects.filter(
                reservation__show=show,
                reservation__status=Reservation.Status.ACTIVE,
                reservation__expires_at__gt=now,
                seat_id__in=seat_ids
            ).exclude(reservation__user=user)

            if active_other_res_seats.exists():
                raise ValueError("One or more selected seats are temporarily reserved by another user.")

            # Release previous active reservations for this user and show
            user_prev_res = Reservation.objects.filter(
                user=user, show=show, status=Reservation.Status.ACTIVE
            )
            for pres in user_prev_res:
                pres.status = Reservation.Status.CANCELLED
                pres.save(update_fields=['status'])
                prev_seat_ids = list(pres.reserved_seats.values_list('seat_id', flat=True))
                ShowSeat.objects.filter(
                    show=show, seat_id__in=prev_seat_ids
                ).exclude(status=ShowSeat.Status.BOOKED).update(status=ShowSeat.Status.AVAILABLE)
                broadcast_seat_update(show.id, prev_seat_ids, ShowSeat.Status.AVAILABLE)

            # Calculate total pricing
            subtotal = Decimal('0.00')
            seat_price_list = []
            for seat in seats:
                seat_cost = (show.ticket_price * seat.price_multiplier).quantize(Decimal('0.01'))
                subtotal += seat_cost
                seat_price_list.append((seat, seat_cost))

            convenience_fee = CONVENIENCE_FEE_PER_TICKET * len(seats)
            grand_total = subtotal + convenience_fee

            expires_at = now + timedelta(minutes=2)

            reservation = Reservation.objects.create(
                user=user,
                show=show,
                status=Reservation.Status.ACTIVE,
                total_amount=grand_total,
                expires_at=expires_at
            )

            res_seats = [
                ReservationSeat(reservation=reservation, seat=seat, price=cost)
                for seat, cost in seat_price_list
            ]
            ReservationSeat.objects.bulk_create(res_seats)

            # Mark ShowSeats as RESERVED
            ShowSeat.objects.filter(show=show, seat_id__in=seat_ids).update(status=ShowSeat.Status.RESERVED)

            # Broadcast real-time update
            broadcast_seat_update(show.id, seat_ids, ShowSeat.Status.RESERVED, user.id)

            return reservation

    @staticmethod
    def modify_seats(user, reservation_id, new_seat_ids):
        """
        Modify existing active reservation with new seat selection atomically.
        """
        with transaction.atomic():
            res = Reservation.objects.select_for_update().get(
                reservation_id=reservation_id,
                user=user,
                status=Reservation.Status.ACTIVE
            )
            if not res.is_valid:
                raise ValueError("Reservation has expired. Please select seats again.")

            return ReservationService.hold_seats(user, res.show_id, new_seat_ids)

    @staticmethod
    def release_reservation(reservation_id, user=None):
        """
        Manually release a reservation and return seats to AVAILABLE.
        """
        with transaction.atomic():
            qs = Reservation.objects.select_for_update().filter(reservation_id=reservation_id)
            if user:
                qs = qs.filter(user=user)
            res = qs.first()
            if not res:
                return False

            if res.status == Reservation.Status.ACTIVE:
                res.status = Reservation.Status.CANCELLED
                res.save(update_fields=['status'])

                seat_ids = list(res.reserved_seats.values_list('seat_id', flat=True))
                ShowSeat.objects.filter(
                    show=res.show, seat_id__in=seat_ids
                ).exclude(status=ShowSeat.Status.BOOKED).update(status=ShowSeat.Status.AVAILABLE)

                broadcast_seat_update(res.show_id, seat_ids, ShowSeat.Status.AVAILABLE)
            return True
