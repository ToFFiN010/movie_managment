from datetime import date, time
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from movies.models import Movie, Language
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, Payment, Booking
from bookings.services import ReservationService, PaymentService

User = get_user_model()


class PaymentTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='payuser', email='pay@test.com', password='password123')
        self.lang = Language.objects.create(name='English', code='en')
        self.movie = Movie.objects.create(
            title='Pay Movie',
            slug='pay-movie',
            description='Desc',
            release_date=date.today(),
            duration_minutes=110,
            language=self.lang,
            director='Dir'
        )
        self.theater = Theater.objects.create(name='Theater 1', city='City')
        self.screen = Screen.objects.create(theater=self.theater, name='Screen 1', screen_number=1, capacity=5)
        self.show = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date.today(),
            start_time=time(14, 0),
            end_time=time(16, 0),
            ticket_price=Decimal('15.00')
        )
        self.seats = list(Seat.objects.filter(screen=self.screen)[:2])
        self.reservation = ReservationService.hold_seats(self.user, self.show.id, [s.id for s in self.seats])

    def test_payment_and_webhook_idempotency(self):
        txn_id = "TXN_TEST_IDEMPOTENT_123"
        payload = {
            'transaction_id': txn_id,
            'idempotency_key': txn_id,
            'reservation_id': self.reservation.reservation_id,
            'user_id': self.user.id,
            'payment_method': Payment.Method.UPI
        }

        # First webhook arrival
        res1 = PaymentService.process_webhook(payload, signature_header="valid_sig")
        self.assertTrue(res1['success'])
        self.assertEqual(res1['status'], 'PROCESSED')

        # Check booking confirmed
        booking = Booking.objects.get(booking_reference=res1['booking_reference'])
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.payment_status, Booking.PaymentStatus.PAID)

        # Duplicate webhook arrival (idempotency check)
        res2 = PaymentService.process_webhook(payload, signature_header="valid_sig")
        self.assertTrue(res2['success'])
        self.assertEqual(res2['status'], 'ALREADY_PROCESSED')

        # Ensure NO duplicate booking created
        self.assertEqual(Booking.objects.filter(reservation=self.reservation).count(), 1)
