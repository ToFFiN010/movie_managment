import os
from datetime import date, time, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from movies.models import Movie, Genre, Language
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, Booking, BookingSeat, Payment, Ticket
from bookings.services.ticket_service import TicketService

class TicketSystemTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ticketuser', email='ticketuser@cineprime.com', password='Password123!')
        self.other_user = User.objects.create_user(username='otheruser', email='otheruser@cineprime.com', password='Password123!')

        self.lang = Language.objects.create(name='English', code='en')
        self.movie = Movie.objects.create(
            title='Inception Ticket Test',
            duration_minutes=148,
            language=self.lang,
            release_date=date(2026, 1, 1),
            status=Movie.Status.NOW_SHOWING
        )
        self.theater = Theater.objects.create(name='CinePrime IMAX', city='Bangalore', address='MG Road')
        self.screen = Screen.objects.create(theater=self.theater, name='Screen 1', screen_number=1, capacity=100)
        self.seat, _ = Seat.objects.get_or_create(screen=self.screen, row='A', seat_number=1, defaults={'seat_type': Seat.SeatType.PREMIUM})

        self.show = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date(2026, 8, 20),
            start_time=time(19, 0),
            end_time=time(21, 30),
            ticket_price=Decimal('250.00'),
            status=ShowSchedule.Status.OPEN
        )

        self.booking = Booking.objects.create(
            user=self.user,
            show=self.show,
            total_amount=Decimal('252.50'),
            status=Booking.Status.CONFIRMED,
            payment_status=Booking.PaymentStatus.PAID
        )
        BookingSeat.objects.create(booking=self.booking, seat=self.seat, price=Decimal('250.00'))
        Payment.objects.create(
            booking=self.booking,
            gateway_order_id='order_test123',
            transaction_id='pay_test123',
            amount=Decimal('252.50'),
            payment_status=Payment.Status.SUCCESS
        )

    def test_ticket_generation_and_idempotency(self):
        # Generate ticket
        ticket1 = TicketService.generate_pdf_ticket(self.booking)
        self.assertIsNotNone(ticket1.ticket_number)
        self.assertTrue(ticket1.ticket_number.startswith('CINE-'))
        self.assertIsNotNone(ticket1.qr_token)

        # File paths exist
        self.assertTrue(os.path.exists(ticket1.pdf_file.path))
        self.assertTrue(os.path.exists(ticket1.qr_code_image.path))

        # Idempotency check: Generating again returns exact same ticket without duplicate
        ticket2 = TicketService.generate_pdf_ticket(self.booking)
        self.assertEqual(ticket1.id, ticket2.id)
        self.assertEqual(Ticket.objects.filter(booking=self.booking).count(), 1)

    def test_download_ticket_authorization(self):
        TicketService.generate_pdf_ticket(self.booking)

        # Owner can download
        self.client.login(username='ticketuser', password='Password123!')
        url = reverse('bookings:download_ticket', kwargs={'booking_ref': self.booking.booking_reference})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Other user gets 403 Forbidden
        self.client.login(username='otheruser', password='Password123!')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_qr_code_verification_route(self):
        ticket = TicketService.generate_pdf_ticket(self.booking)
        
        # Valid ticket QR scan
        url = reverse('bookings:verify_ticket', kwargs={'qr_token': ticket.qr_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TICKET VERIFIED')
        self.assertContains(response, 'Inception Ticket Test')

        # Invalid token QR scan
        invalid_url = reverse('bookings:verify_ticket', kwargs={'qr_token': 'invalid_token_123'})
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'INVALID OR EXPIRED TICKET')
