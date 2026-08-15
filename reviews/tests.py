from datetime import date, time
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from movies.models import Movie, Language
from theaters.models import Theater, Screen
from bookings.models import ShowSchedule, Booking
from reviews.models import Review

class ReviewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reviewer', password='password123', email='rev@example.com')
        self.lang = Language.objects.create(name='English', code='en')
        self.movie = Movie.objects.create(
            title='Gladiator',
            description='Roman epic.',
            release_date=date(2000, 5, 5),
            duration_minutes=155,
            language=self.lang,
            director='Ridley Scott'
        )
        self.theater = Theater.objects.create(name='Empire', location='Center', address='1 Main St', city='Rome')
        self.screen = Screen.objects.create(theater=self.theater, screen_number=1, capacity=20)
        self.show = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date.today(),
            start_time=time(10, 0),
            end_time=time(12, 30),
            ticket_price=Decimal('12.00')
        )
        self.booking = Booking.objects.create(
            user=self.user,
            show=self.show,
            total_amount=Decimal('12.00'),
            status=Booking.Status.CONFIRMED,
            payment_status=Booking.PaymentStatus.PAID
        )

    def test_review_creation_and_verified_badge(self):
        review = Review.objects.create(
            user=self.user,
            movie=self.movie,
            booking=self.booking,
            rating=5,
            review_text='Awesome cinematic experience!',
            status=Review.Status.APPROVED
        )
        self.assertTrue(review.is_verified_viewer)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.average_rating, 5.0)
        self.assertEqual(self.movie.total_reviews, 1)
