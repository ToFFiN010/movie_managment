from datetime import date, time
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from accounts.models import User
from movies.models import Movie, Language
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, Booking, BookingSeat, Payment

class BookingsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='password123', email='buyer@example.com')
        self.lang = Language.objects.create(name='English', code='en')
        self.movie = Movie.objects.create(
            title='Interstellar',
            description='Space exploration.',
            release_date=date(2014, 11, 7),
            duration_minutes=169,
            language=self.lang,
            director='Christopher Nolan'
        )
        self.theater = Theater.objects.create(name='Grand Cinema', location='Center', address='1 Main St', city='Boston')
        self.screen = Screen.objects.create(theater=self.theater, screen_number=1, capacity=20)
        self.screen.generate_seats()
        self.show = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date.today(),
            start_time=time(14, 0),
            end_time=time(17, 0),
            ticket_price=Decimal('10.00')
        )
        self.seat = Seat.objects.filter(screen=self.screen).first()

    def test_schedule_overlap_validation(self):
        overlapping_show = ShowSchedule(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date.today(),
            start_time=time(15, 0), # Overlaps with 14:00 - 17:00
            end_time=time(18, 0),
            ticket_price=Decimal('10.00')
        )
        with self.assertRaises(ValidationError):
            overlapping_show.full_clean()

    def test_booking_creation_and_payment_flow(self):
        self.client.login(username='buyer', password='password123')
        
        # Post seat selection to create pending booking
        response = self.client.post(reverse('bookings:create_booking', kwargs={'show_id': self.show.id}), {
            'selected_seats': str(self.seat.id)
        })
        self.assertEqual(response.status_code, 302)
        
        booking = Booking.objects.get(user=self.user, show=self.show)
        self.assertEqual(booking.status, Booking.Status.PENDING)

        # Checkout view rendering
        checkout_response = self.client.get(reverse('bookings:checkout', kwargs={'booking_ref': booking.booking_reference}))
        self.assertEqual(checkout_response.status_code, 200)
        
        booking.status = Booking.Status.CONFIRMED
        booking.payment_status = Booking.PaymentStatus.PAID
        booking.save()

        confirm_response = self.client.get(reverse('bookings:confirmation', kwargs={'booking_ref': booking.booking_reference}))
        self.assertEqual(confirm_response.status_code, 200)
