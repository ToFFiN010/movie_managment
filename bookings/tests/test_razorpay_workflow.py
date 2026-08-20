import json
import hmac
import hashlib
from datetime import date, time, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status

from movies.models import Movie, Language
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, Payment, Booking, ShowSeat, BookingSeat
from bookings.services import PaymentService, release_expired_bookings

User = get_user_model()


class RazorpayWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(username='usera', email='usera@test.com', password='password123')
        self.user_b = User.objects.create_user(username='userb', email='userb@test.com', password='password123')

        self.lang = Language.objects.create(name='Hindi', code='hi')
        self.movie = Movie.objects.create(
            title='Spider-Man: Brand New Day',
            slug='spider-man-brand-new-day',
            description='Hero movie',
            release_date=date.today(),
            duration_minutes=150,
            language=self.lang,
            director='Director'
        )

        self.theater = Theater.objects.create(name='PVR Cinema', city='Mumbai')
        self.screen = Screen.objects.create(theater=self.theater, name='IMAX Screen 1', screen_number=1, capacity=10)
        
        self.screen.generate_seats()
        self.seats = list(Seat.objects.filter(screen=self.screen)[:5])

        self.show = ShowSchedule.objects.create(
            movie=self.movie,
            theater=self.theater,
            screen=self.screen,
            show_date=date.today(),
            start_time=time(18, 0),
            end_time=time(21, 0),
            ticket_price=Decimal('200.00')
        )

    def test_successful_payment_order_and_verification(self):
        self.client.force_authenticate(user=self.user_a)
        
        # Step 1: Create Order via API
        seat_ids = [self.seats[0].id, self.seats[1].id]
        response = self.client.post('/api/v1/bookings/create/', {
            'show_id': self.show.id,
            'seat_ids': seat_ids
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        booking_ref = response.data['booking_reference']
        order_id = response.data['razorpay_order_id']

        # Verify PENDING Booking and Payment created
        booking = Booking.objects.get(booking_reference=booking_ref)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.payment_status, Booking.PaymentStatus.PENDING)
        
        # Verify seats reserved
        for sid in seat_ids:
            ss = ShowSeat.objects.get(show=self.show, seat_id=sid)
            self.assertEqual(ss.status, ShowSeat.Status.RESERVED)

        # Step 2: Server-side Payment Verification
        payment_id = "pay_test_signature_123"
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', 'cineprime_secret_key_123456')
        signature = hmac.new(key_secret.encode('utf-8'), f"{order_id}|{payment_id}".encode('utf-8'), hashlib.sha256).hexdigest()

        verify_response = self.client.post('/api/v1/payments/verify/', {
            'booking_reference': booking_ref,
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }, format='json')

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertTrue(verify_response.data['success'])

        # Verify Booking and Payment updated to CONFIRMED and SUCCESS
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.payment_status, Booking.PaymentStatus.PAID)
        
        for sid in seat_ids:
            ss = ShowSeat.objects.get(show=self.show, seat_id=sid)
            self.assertEqual(ss.status, ShowSeat.Status.BOOKED)

    def test_failed_payment_releases_seats(self):
        self.client.force_authenticate(user=self.user_a)
        seat_ids = [self.seats[2].id]

        response = self.client.post('/api/v1/bookings/create/', {
            'show_id': self.show.id,
            'seat_ids': seat_ids
        }, format='json')
        booking_ref = response.data['booking_reference']

        # Cancel payment explicitly via PaymentService
        cancelled = PaymentService.cancel_payment(self.user_a, booking_ref)
        self.assertTrue(cancelled)

        booking = Booking.objects.get(booking_reference=booking_ref)
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

        # Verify seat is released back to AVAILABLE
        ss = ShowSeat.objects.get(show=self.show, seat_id=self.seats[2].id)
        self.assertEqual(ss.status, ShowSeat.Status.AVAILABLE)

    def test_duplicate_webhook_idempotency(self):
        # Create order
        order_data = PaymentService.create_booking_and_razorpay_order(
            user=self.user_a,
            show=self.show,
            seats=[self.seats[0]]
        )
        order_id = order_data['razorpay_order_id']
        booking_ref = order_data['booking_reference']

        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', 'cineprime_webhook_secret_123456')
        payload_dict = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_123',
                        'order_id': order_id,
                        'amount': order_data['amount'],
                        'status': 'captured'
                    }
                }
            }
        }
        body_bytes = json.dumps(payload_dict).encode('utf-8')
        signature = hmac.new(webhook_secret.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()

        # Webhook #1
        res1 = PaymentService.process_webhook(body_bytes, signature)
        self.assertTrue(res1['success'])
        self.assertEqual(res1['status'], 'CONFIRMED')

        # Webhook #2 (Duplicate)
        res2 = PaymentService.process_webhook(body_bytes, signature)
        self.assertTrue(res2['success'])
        self.assertEqual(res2['status'], 'ALREADY_PROCESSED')

        # Ensure exactly 1 booking exists
        self.assertEqual(Booking.objects.filter(booking_reference=booking_ref).count(), 1)

    def test_callback_and_webhook_race_condition(self):
        order_data = PaymentService.create_booking_and_razorpay_order(
            user=self.user_a,
            show=self.show,
            seats=[self.seats[1]]
        )
        order_id = order_data['razorpay_order_id']
        booking_ref = order_data['booking_reference']
        payment_id = "pay_race_123"

        # Webhook processes first
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', 'cineprime_webhook_secret_123456')
        payload_dict = {
            'event': 'payment.captured',
            'payload': {'payment': {'entity': {'id': payment_id, 'order_id': order_id}}}
        }
        body_bytes = json.dumps(payload_dict).encode('utf-8')
        signature = hmac.new(webhook_secret.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()
        PaymentService.process_webhook(body_bytes, signature)

        # Frontend verification arrives second
        booking = PaymentService.verify_payment(
            user=self.user_a,
            booking_reference=booking_ref,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature="dummy_sig"
        )
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(Booking.objects.filter(booking_reference=booking_ref).count(), 1)

    def test_payment_retry_workflow(self):
        # Create booking for user_a
        order_data = PaymentService.create_booking_and_razorpay_order(
            user=self.user_a,
            show=self.show,
            seats=[self.seats[0]]
        )
        booking_ref = order_data['booking_reference']

        # Cancel attempt 1 via service
        PaymentService.cancel_payment(self.user_a, booking_ref)

        # Retry payment attempt 2
        retry_data = PaymentService.retry_payment(self.user_a, booking_ref)
        self.assertIsNotNone(retry_data.get('razorpay_order_id'))
        new_order_id = retry_data['razorpay_order_id']

        # Confirm attempt 2
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', 'cineprime_secret_key_123456')
        payment_id = "pay_retry_success_999"
        sig = hmac.new(key_secret.encode('utf-8'), f"{new_order_id}|{payment_id}".encode('utf-8'), hashlib.sha256).hexdigest()

        booking = PaymentService.verify_payment(
            user=self.user_a,
            booking_reference=booking_ref,
            razorpay_order_id=new_order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=sig
        )

        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.payment_status, Booking.PaymentStatus.PAID)

    def test_double_booking_prevention(self):
        # User A reserves Seat A1
        PaymentService.create_booking_and_razorpay_order(
            user=self.user_a,
            show=self.show,
            seats=[self.seats[0]]
        )

        # User B attempts to reserve Seat A1
        with self.assertRaises(ValueError):
            PaymentService.create_booking_and_razorpay_order(
                user=self.user_b,
                show=self.show,
                seats=[self.seats[0]]
            )

    def test_unauthorized_access_prevention(self):
        # Create booking for User A
        order_data = PaymentService.create_booking_and_razorpay_order(
            user=self.user_a,
            show=self.show,
            seats=[self.seats[0]]
        )
        booking_ref = order_data['booking_reference']

        # User B attempts to verify User A's payment
        self.client.force_authenticate(user=self.user_b)
        response = self.client.post('/api/v1/payments/verify/', {
            'booking_reference': booking_ref,
            'razorpay_order_id': order_data['razorpay_order_id'],
            'razorpay_payment_id': 'pay_hack_123',
            'razorpay_signature': 'hack_sig'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_reservation_seat_release(self):
        order_data = PaymentService.create_booking_and_razorpay_order(
            user=self.user_a,
            show=self.show,
            seats=[self.seats[3]]
        )
        booking = Booking.objects.get(booking_reference=order_data['booking_reference'])

        # Manually expire reservation time
        booking.reservation_expires_at = timezone.now() - timedelta(minutes=1)
        booking.save()

        # Run seat release command/service
        released_count = release_expired_bookings()
        self.assertGreaterEqual(released_count, 1)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        ss = ShowSeat.objects.get(show=self.show, seat_id=self.seats[3].id)
        self.assertEqual(ss.status, ShowSeat.Status.AVAILABLE)
