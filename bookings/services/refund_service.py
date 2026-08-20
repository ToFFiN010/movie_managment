import logging
from decimal import Decimal
from django.db import transaction
from bookings.models import Booking, Payment, Refund, ShowSeat
from notifications.models import Notification
from .reservation_service import broadcast_seat_update

logger = logging.getLogger(__name__)


class RefundService:
    @staticmethod
    def process_cancellation_and_refund(booking_ref, user, reason="User requested cancellation"):
        """
        Atomically cancels a booking, marks seats as available, and creates refund.
        """
        with transaction.atomic():
            booking = Booking.objects.select_for_update().select_related('show').get(
                booking_reference=booking_ref,
                user=user
            )

            if booking.status == Booking.Status.CANCELLED:
                raise ValueError("Booking has already been cancelled.")

            booking.status = Booking.Status.CANCELLED
            booking.payment_status = Booking.PaymentStatus.REFUNDED
            booking.save(update_fields=['status', 'payment_status'])

            # Free booked seats back to AVAILABLE
            booked_seat_ids = list(booking.booked_seats.values_list('seat_id', flat=True))
            ShowSeat.objects.filter(
                show=booking.show,
                seat_id__in=booked_seat_ids
            ).update(status=ShowSeat.Status.AVAILABLE)

            broadcast_seat_update(booking.show_id, booked_seat_ids, ShowSeat.Status.AVAILABLE)

            # Create Refund record
            payment = getattr(booking, 'payment', None)
            refund = Refund.objects.create(
                booking=booking,
                payment=payment,
                amount=booking.total_amount,
                reason=reason,
                status=Refund.Status.PROCESSED
            )

            if payment:
                payment.payment_status = Payment.Status.FAILED
                payment.save(update_fields=['payment_status'])

            # Create Notification
            Notification.objects.create(
                user=user,
                title="Booking Cancelled & Refund Initiated",
                message=f"Booking {booking.booking_reference} for '{booking.show.movie.title}' was cancelled. Refund of ${booking.total_amount} processed.",
                notification_type=Notification.Type.CANCELLATION
            )

            return refund
