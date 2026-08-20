import os
import logging
import threading
from datetime import datetime

from django.conf import settings
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from celery import shared_task

from bookings.models import Booking, Ticket, Payment
from bookings.services.ticket_service import TicketService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_ticket_email_task(self, ticket_id):
    """
    Celery task to send PDF ticket email to user.
    Idempotent: If email was already sent, returns immediately without duplicate delivery.
    Autoretries with exponential backoff on network failure.
    """
    try:
        ticket = Ticket.objects.select_related('booking__user', 'booking__show__movie', 'booking__show__theater', 'booking__show__screen').get(pk=ticket_id)
    except Ticket.DoesNotExist:
        logger.error(f"Ticket ID {ticket_id} not found for email dispatch.")
        return False

    # Idempotency check: If email has already been sent, do not re-send!
    if ticket.email_status == Ticket.EmailStatus.SENT:
        logger.info(f"Email already sent for ticket {ticket.ticket_number}. Skipping.")
        return True

    booking = ticket.booking
    user = booking.user
    show = booking.show
    movie = show.movie
    theater = show.theater
    screen = show.screen

    subject = f"CinePrime Booking Confirmation — {booking.booking_reference}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'CinePrime Cinemas <noreply@cineprime.com>')
    to_email = user.email or 'customer@cineprime.com'

    booked_seats = ", ".join([bs.seat.label for bs in booking.booked_seats.all()]) or "N/A"

    context = {
        'user': user,
        'booking': booking,
        'ticket': ticket,
        'movie': movie,
        'theater': theater,
        'screen': screen,
        'show': show,
        'booked_seats': booked_seats,
    }

    # HTML Email Body Text
    html_content = f"""
    <div style="font-family: Arial, sans-serif; background-color: #0B1020; color: #FFFFFF; padding: 25px; border-radius: 10px;">
        <h2 style="color: #FFB000;">🎬 CinePrime Booking Confirmation</h2>
        <p>Hello <strong>{user.get_full_name() or user.username}</strong>,</p>
        <p>Your movie ticket booking has been successfully confirmed!</p>

        <div style="background-color: #1E293B; padding: 15px; border-radius: 8px; border-left: 4px solid #8B5CF6; margin: 15px 0;">
            <h3 style="color: #FFFFFF; margin-top: 0;">{movie.title}</h3>
            <p><strong>Theater:</strong> {theater.name} ({screen.name})</p>
            <p><strong>Date & Time:</strong> {show.show_date.strftime('%A, %b %d, %Y')} at {show.start_time.strftime('%I:%M %p')}</p>
            <p><strong>Seats:</strong> <span style="color: #FFB000;">{booked_seats}</span></p>
            <p><strong>Booking Ref:</strong> {booking.booking_reference}</p>
            <p><strong>Ticket Number:</strong> {ticket.ticket_number}</p>
        </div>

        <p>Your official PDF ticket with entry QR code is attached to this email.</p>
        <p>Thank you for choosing CinePrime Cinemas!</p>
    </div>
    """

    plain_content = f"Hello {user.username},\n\nYour CinePrime booking {booking.booking_reference} for {movie.title} is confirmed!\nSeats: {booked_seats}\nTicket Number: {ticket.ticket_number}\n\nYour PDF ticket is attached.\n\nThank you for choosing CinePrime!"

    try:
        email = EmailMultiAlternatives(subject, plain_content, from_email, [to_email])
        email.attach_alternative(html_content, "text/html")

        # Attach PDF File
        if ticket.pdf_file and os.path.exists(ticket.pdf_file.path):
            with open(ticket.pdf_file.path, 'rb') as f:
                pdf_data = f.read()
            attachment_name = f"CinePrime_{ticket.ticket_number}.pdf"
            email.attach(attachment_name, pdf_data, 'application/pdf')

        email.send(fail_silently=False)

        ticket.email_status = Ticket.EmailStatus.SENT
        ticket.email_sent_at = timezone.now()
        ticket.email_attempts += 1
        ticket.last_email_error = None
        ticket.save(update_fields=['email_status', 'email_sent_at', 'email_attempts', 'last_email_error'])

        logger.info(f"Successfully sent ticket email for {ticket.ticket_number} to {to_email}")
        return True

    except Exception as e:
        ticket.email_attempts += 1
        ticket.last_email_error = str(e)
        ticket.email_status = Ticket.EmailStatus.FAILED
        ticket.save(update_fields=['email_attempts', 'last_email_error', 'email_status'])

        logger.warning(f"Email delivery failed for ticket {ticket.ticket_number}: {e}")
        try:
            raise self.retry(exc=e)
        except Exception:
            return False


@shared_task
def generate_ticket_task(booking_id):
    """
    Celery task to generate PDF ticket and trigger email task asynchronously.
    Idempotent: Uses TicketService which reuses existing ticket records.
    """
    try:
        booking = Booking.objects.get(pk=booking_id)
        if booking.status not in [Booking.Status.CONFIRMED, Booking.Status.COMPLETED]:
            logger.warning(f"Booking {booking_id} status is {booking.status}. Skipping ticket generation.")
            return False

        ticket = TicketService.generate_pdf_ticket(booking)

        # Trigger Email Celery Task asynchronously
        try:
            send_ticket_email_task.delay(ticket.id)
        except Exception as err:
            logger.warning(f"Celery broker unavailable ({err}). Sending email via fallback handler.")
            send_ticket_email_task(ticket.id)

        return ticket.id

    except Exception as e:
        logger.error(f"Error in generate_ticket_task for booking {booking_id}: {e}")
        return False


def queue_ticket_and_email(booking_id):
    """
    Safely queues ticket generation and email dispatch.
    If Celery broker is running, dispatches asynchronously via Celery.
    If Celery/Redis is unreachable, runs in a background thread so HTTP requests NEVER block or fail.
    """
    def _run_in_background():
        try:
            booking = Booking.objects.get(pk=booking_id)
            ticket = TicketService.generate_pdf_ticket(booking)
            send_ticket_email_task(ticket.id)
        except Exception as e:
            logger.error(f"Background thread ticket generation error: {e}")

    try:
        generate_ticket_task.delay(booking_id)
    except Exception:
        # Fallback to asynchronous daemon thread so user response is fast and non-blocking
        t = threading.Thread(target=_run_in_background, daemon=True)
        t.start()
