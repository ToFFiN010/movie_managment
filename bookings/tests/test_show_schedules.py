from datetime import date, time, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from accounts.models import User
from movies.models import Movie, Language
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, ShowSeat

class ShowScheduleTestCase(TestCase):
    def setUp(self):
        self.lang = Language.objects.create(name='English', code='en')
        self.movie = Movie.objects.create(
            title='ShowSchedule Test Movie',
            duration_minutes=120,
            language=self.lang,
            release_date=date(2026, 1, 1),
            status=Movie.Status.NOW_SHOWING
        )
        self.theater = Theater.objects.create(name='Showtime CinePlex', city='Mumbai', address='Andheri West')
        self.screen = Screen.objects.create(theater=self.theater, name='Screen 1', screen_number=1, capacity=50)

    def test_show_schedule_creation_and_seats_generation(self):
        show = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date(2026, 8, 25),
            start_time=time(10, 0),
            end_time=time(13, 0),
            ticket_price=Decimal('200.00'),
            status=ShowSchedule.Status.OPEN
        )
        self.assertEqual(show.status, ShowSchedule.Status.OPEN)
        self.assertEqual(show.show_seats.count(), self.screen.seats.count())

    def test_invalid_start_end_time_validation(self):
        show = ShowSchedule(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date(2026, 8, 25),
            start_time=time(14, 0),
            end_time=time(12, 0), # End time before start time
            ticket_price=Decimal('200.00'),
            status=ShowSchedule.Status.OPEN
        )
        with self.assertRaises(ValidationError):
            show.clean()

    def test_overlapping_showtime_validation(self):
        # First show 10:00 - 13:00
        ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date(2026, 8, 25),
            start_time=time(10, 0),
            end_time=time(13, 0),
            ticket_price=Decimal('200.00'),
            status=ShowSchedule.Status.OPEN
        )

        # Overlapping show 11:30 - 14:30 on same screen
        overlapping_show = ShowSchedule(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date(2026, 8, 25),
            start_time=time(11, 30),
            end_time=time(14, 30),
            ticket_price=Decimal('200.00'),
            status=ShowSchedule.Status.OPEN
        )
        with self.assertRaises(ValidationError):
            overlapping_show.clean()

    def test_independent_seat_availability_per_showtime(self):
        show1 = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date(2026, 8, 25),
            start_time=time(10, 0),
            end_time=time(13, 0),
            ticket_price=Decimal('200.00')
        )
        show2 = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date(2026, 8, 25),
            start_time=time(14, 0),
            end_time=time(17, 0),
            ticket_price=Decimal('200.00')
        )

        seat = self.screen.seats.first()
        show1_seat = ShowSeat.objects.get(show=show1, seat=seat)
        show2_seat = ShowSeat.objects.get(show=show2, seat=seat)

        # Mark seat booked for show1 only
        show1_seat.status = ShowSeat.Status.BOOKED
        show1_seat.save()

        # show2_seat remains AVAILABLE independently
        show2_seat.refresh_from_db()
        self.assertEqual(show1_seat.status, ShowSeat.Status.BOOKED)
        self.assertEqual(show2_seat.status, ShowSeat.Status.AVAILABLE)
