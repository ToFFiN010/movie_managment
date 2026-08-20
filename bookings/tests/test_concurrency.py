import threading
from datetime import date, time
from decimal import Decimal
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from movies.models import Movie, Language
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule
from bookings.services import ReservationService

User = get_user_model()


class ConcurrencyTestCase(TransactionTestCase):
    """
    Critical concurrency test suite.
    Simulates multiple concurrent threads attempting to reserve the exact same seat simultaneously.
    Verifies that database-level atomic locking guarantees that only ONE reservation succeeds.
    """
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', email='user1@test.com', password='password123')
        self.user2 = User.objects.create_user(username='user2', email='user2@test.com', password='password123')

        self.lang = Language.objects.create(name='English', code='en')
        self.movie = Movie.objects.create(
            title='Inception Concurrency',
            slug='inception-concurrency',
            description='Test movie',
            release_date=date.today(),
            duration_minutes=148,
            language=self.lang,
            director='Christopher Nolan'
        )
        self.theater = Theater.objects.create(
            name='CinePrime IMAX',
            location='Downtown',
            address='123 Cinema Street',
            city='Metropolis'
        )
        self.screen = Screen.objects.create(
            theater=self.theater,
            name='Screen 1',
            screen_number=1,
            capacity=10
        )
        self.show = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date.today(),
            start_time=time(18, 0),
            end_time=time(20, 30),
            ticket_price=Decimal('12.00')
        )
        self.screen.generate_seats()
        self.target_seat = Seat.objects.filter(screen=self.screen).first()

    def test_simultaneous_seat_reservation_concurrency(self):
        results = []
        errors = []

        def attempt_reservation(user, delay=0):
            import time as pytime
            if delay:
                pytime.sleep(delay)
            from django.db import connections
            connections.close_all()
            try:
                res = ReservationService.hold_seats(user, self.show.id, [self.target_seat.id])
                results.append((user.username, res.reservation_id))
            except Exception as e:
                errors.append((user.username, str(e)))

        t1 = threading.Thread(target=attempt_reservation, args=(self.user1, 0))
        t2 = threading.Thread(target=attempt_reservation, args=(self.user2, 0.02))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Exactly 1 reservation must succeed
        self.assertEqual(len(results), 1, "Only one user reservation should succeed for the same seat.")
        self.assertEqual(len(errors), 1, "The second user reservation should fail due to seat lock.")
