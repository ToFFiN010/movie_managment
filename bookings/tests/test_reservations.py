from datetime import date, time, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from movies.models import Movie, Language
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, Reservation, ShowSeat
from bookings.services import ReservationService, release_expired_reservations_for_show

User = get_user_model()


class ReservationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@cineprime.com', password='password123')
        self.lang = Language.objects.create(name='English', code='en')
        self.movie = Movie.objects.create(
            title='Test Movie',
            slug='test-movie',
            description='Description',
            release_date=date.today(),
            duration_minutes=120,
            language=self.lang,
            director='Director'
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
            ticket_price=Decimal('10.00')
        )
        self.seats = list(Seat.objects.filter(screen=self.screen)[:2])

    def test_reservation_hold_and_expiration(self):
        res = ReservationService.hold_seats(self.user, self.show.id, [s.id for s in self.seats])
        self.assertTrue(res.is_valid)
        self.assertEqual(res.status, Reservation.Status.ACTIVE)

        # Verify ShowSeats marked as RESERVED
        show_seats = ShowSeat.objects.filter(show=self.show, seat_id__in=[s.id for s in self.seats])
        for ss in show_seats:
            self.assertEqual(ss.status, ShowSeat.Status.RESERVED)

        # Force expiration timestamp into the past
        res.expires_at = timezone.now() - timedelta(minutes=1)
        res.save()

        self.assertFalse(res.is_valid)

        # Run expiration cleanup
        count = release_expired_reservations_for_show(self.show.id)
        self.assertEqual(count, 1)

        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.Status.EXPIRED)

        # Verify ShowSeats returned to AVAILABLE
        for ss in show_seats:
            ss.refresh_from_db()
            self.assertEqual(ss.status, ShowSeat.Status.AVAILABLE)
