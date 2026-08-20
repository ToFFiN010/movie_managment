import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from bookings.models import Reservation, Booking, BookingSeat, ShowSeat, Payment, Coupon
from notifications.models import Notification
from .reservation_service import broadcast_seat_update
from .ticket_service import TicketService

logger = logging.getLogger(__name__)


class BookingService:
    @staticmethod
    def create_booking_from_reservation(reservation_id, user, payment_method=Payment.Method.UPI, coupon_code=None, idempotency_key=None, transaction_id=None):
        """
        Atomically converts an active Reservation into a CONFIRMED Booking upon successful payment.
        """
        with transaction.atomic():
            res = Reservation.objects.select_for_update().get(
                reservation_id=reservation_id,
                user=user
            )

            if res.status == Reservation.Status.CONVERTED:
                # Return existing booking for idempotency
                if hasattr(res, 'booking'):
                    return res.booking
                raise ValueError("Reservation has already been processed.")

            if not res.is_valid:
                res.status = Reservation.Status.EXPIRED
                res.save(update_fields=['status'])
                raise ValueError("Reservation timer has expired. Please re-select your seats.")

            # Calculate discount if coupon is supplied
            discount_amount = Decimal('0.00')
            if coupon_code:
                coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first()
                if coupon and coupon.is_valid(res.total_amount):
                    discount_amount = coupon.calculate_discount(res.total_amount)

            final_total = max(Decimal('0.00'), res.total_amount - discount_amount)

            # Create Booking
            booking = Booking.objects.create(
                user=user,
                show=res.show,
                reservation=res,
                total_amount=final_total,
                discount_amount=discount_amount,
                coupon_code=coupon_code,
                status=Booking.Status.CONFIRMED,
                payment_status=Booking.PaymentStatus.PAID
            )

            # Mark Reservation as CONVERTED
            res.status = Reservation.Status.CONVERTED
            res.save(update_fields=['status'])

            # Create BookingSeats and update ShowSeat status to BOOKED
            seat_ids = []
            for r_seat in res.reserved_seats.all():
                BookingSeat.objects.create(
                    booking=booking,
                    seat=r_seat.seat,
                    price=r_seat.price
                )
                seat_ids.append(r_seat.seat_id)

            ShowSeat.objects.filter(
                show=res.show,
                seat_id__in=seat_ids
            ).update(status=ShowSeat.Status.BOOKED)

            # Create Payment record
            if not transaction_id:
                transaction_id = f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{booking.id}"

            Payment.objects.create(
                booking=booking,
                transaction_id=transaction_id,
                payment_method=payment_method,
                amount=final_total,
                payment_status=Payment.Status.SUCCESS,
                idempotency_key=idempotency_key or transaction_id
            )

            # Generate PDF ticket
            TicketService.generate_pdf_ticket(booking)

            # Broadcast WS update
            broadcast_seat_update(res.show_id, seat_ids, ShowSeat.Status.BOOKED, user.id)

            # Send Notification
            Notification.objects.create(
                user=user,
                title="Booking Confirmed! 🎉",
                message=f"Your ticket for '{res.show.movie.title}' at {res.show.theater.name} (Ref: {booking.booking_reference}) is confirmed.",
                notification_type=Notification.Type.BOOKING
            )

            return booking
