from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.shortcuts import get_object_or_404

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # Skip CSRF enforcement for JSON API endpoints while keeping session authentication

from bookings.models import (
    ShowSchedule, Seat, ShowSeat, Reservation, ReservationSeat,
    Booking, BookingSeat, Payment, Coupon, Refund
)
from movies.models import Movie
from theaters.models import Theater
from accounts.models import User, AuditLog
from bookings.serializers import (
    ShowSeatSerializer, ReservationSerializer, BookingDetailSerializer,
    CouponSerializer, RefundSerializer, AuditLogSerializer
)
from bookings.services import (
    ReservationService, BookingService, PaymentService,
    RefundService, release_expired_reservations_for_show,
    release_expired_bookings
)

CONVENIENCE_FEE_PER_TICKET = Decimal('2.50')


class ShowSeatLayoutAPIView(APIView):
    """
    GET /api/v1/shows/<show_id>/seats/
    Returns full seat map layout and live status for a show.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, show_id):
        try:
            show = ShowSchedule.objects.select_related('movie', 'theater', 'screen').get(pk=show_id)
        except ShowSchedule.DoesNotExist:
            return Response({'success': False, 'message': 'Show not found'}, status=status.HTTP_404_NOT_FOUND)

        # Release stale reservations and bookings first
        release_expired_reservations_for_show(show_id)
        release_expired_bookings()

        seats = Seat.objects.filter(screen=show.screen, is_active=True).order_by('row', 'seat_number')

        # Build set of booked seats (confirmed or completed)
        booked_seat_ids = set(BookingSeat.objects.filter(
            booking__show=show,
            booking__status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]
        ).values_list('seat_id', flat=True))

        # Build set of locked/reserved seats (pending active bookings)
        now = timezone.now()
        locked_seat_ids = set(BookingSeat.objects.filter(
            booking__show=show,
            booking__status=Booking.Status.PENDING,
            booking__reservation_expires_at__gt=now
        ).values_list('seat_id', flat=True))

        # Build set of actively reserved seats from Reservation model
        active_reservations = Reservation.objects.filter(
            show=show,
            status=Reservation.Status.ACTIVE,
            expires_at__gt=now
        ).prefetch_related('reserved_seats')

        reserved_by_user = set()
        reserved_by_others = set()

        for res in active_reservations:
            res_seat_ids = set(res.reserved_seats.values_list('seat_id', flat=True))
            if request.user.is_authenticated and res.user_id == request.user.id:
                reserved_by_user.update(res_seat_ids)
            else:
                reserved_by_others.update(res_seat_ids)

        seat_grid = {}
        for seat in seats:
            ticket_cost = (show.ticket_price * seat.price_multiplier).quantize(Decimal('0.01'))

            if seat.id in booked_seat_ids:
                seat_status = 'BOOKED'
            elif seat.id in locked_seat_ids or seat.id in reserved_by_others:
                seat_status = 'RESERVED'
            elif seat.id in reserved_by_user:
                seat_status = 'SELECTED_BY_ME'
            else:
                seat_status = 'AVAILABLE'

            seat_data = {
                'id': seat.id,
                'number': seat.seat_number,
                'label': seat.label,
                'seat_type': seat.seat_type,
                'status': seat_status,
                'price': str(ticket_cost)
            }
            seat_grid.setdefault(seat.row, []).append(seat_data)

        return Response({
            'success': True,
            'show_id': show.id,
            'movie_title': show.movie.title,
            'theater_name': show.theater.name,
            'screen_name': show.screen.name,
            'base_price': str(show.ticket_price),
            'convenience_fee': str(CONVENIENCE_FEE_PER_TICKET),
            'seat_grid': seat_grid
        })


@method_decorator(csrf_exempt, name='dispatch')
class CreateBookingOrderAPIView(APIView):
    """
    POST /api/v1/bookings/create/ or /api/v1/payments/create-order/
    Creates PENDING booking, locks seats, calculates server amount, returns Razorpay order.
    """
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        show_id = request.data.get('show_id')
        seat_ids = request.data.get('seat_ids', [])
        coupon_code = request.data.get('coupon_code')
        payment_method = request.data.get('payment_method', Payment.Method.UPI)

        if not show_id or not seat_ids:
            return Response({'success': False, 'message': 'show_id and seat_ids are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            show = ShowSchedule.objects.get(pk=show_id)
            seats = list(Seat.objects.filter(id__in=seat_ids, screen=show.screen, is_active=True))
            if len(seats) != len(seat_ids):
                return Response({'success': False, 'message': 'One or more selected seats are invalid.'}, status=status.HTTP_400_BAD_REQUEST)

            order_data = PaymentService.create_booking_and_razorpay_order(
                user=request.user,
                show=show,
                seats=seats,
                coupon_code=coupon_code,
                payment_method=payment_method
            )
            return Response({
                'success': True,
                'message': 'Booking order created successfully. Proceed to Razorpay payment.',
                **order_data
            }, status=status.HTTP_201_CREATED)
        except ValueError as ve:
            return Response({'success': False, 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPaymentAPIView(APIView):
    """
    POST /api/v1/payments/verify/
    Verifies Razorpay payment server-side and confirms booking idempotently.
    """
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        booking_ref = request.data.get('booking_reference') or request.data.get('booking_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not booking_ref or not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
            return Response({'success': False, 'message': 'Missing required payment verification fields.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # If numeric ID sent instead of string reference
            if isinstance(booking_ref, int) or (isinstance(booking_ref, str) and booking_ref.isdigit()):
                booking_obj = Booking.objects.filter(id=int(booking_ref), user=request.user).first()
                if booking_obj:
                    booking_ref = booking_obj.booking_reference

            booking = PaymentService.verify_payment(
                user=request.user,
                booking_reference=booking_ref,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature
            )
            return Response({
                'success': True,
                'message': 'Payment verified successfully! Booking confirmed.',
                'booking': BookingDetailSerializer(booking).data
            }, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response({'success': False, 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetryPaymentAPIView(APIView):
    """
    POST /api/v1/payments/<booking_ref>/retry/
    Creates a new Razorpay order for retrying a failed or pending booking.
    """
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_ref):
        try:
            order_data = PaymentService.retry_payment(request.user, booking_ref)
            return Response({
                'success': True,
                'message': 'New payment order generated for retry.',
                **order_data
            })
        except ValueError as ve:
            return Response({'success': False, 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CancelPaymentAPIView(APIView):
    """
    POST /api/v1/payments/<booking_ref>/cancel/
    Handles payment cancellation by user, releases seats.
    """
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_ref):
        cancelled = PaymentService.cancel_payment(request.user, booking_ref)
        if cancelled:
            return Response({'success': True, 'message': 'Payment cancelled and seats released.'})
        return Response({'success': False, 'message': 'Unable to cancel payment or booking already confirmed.'}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookAPIView(APIView):
    """
    POST /api/v1/payments/webhook/
    Server-side idempotent Razorpay webhook receiver.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        signature = request.headers.get('X-Razorpay-Signature') or request.headers.get('X-Signature', '')
        result = PaymentService.process_webhook(request.body, signature)
        return Response(result, status=status.HTTP_200_OK if result.get('success') else status.HTTP_400_BAD_REQUEST)


class PaymentHistoryAPIView(APIView):
    """
    GET /api/v1/payments/history/
    Returns payment history for the authenticated user only.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(booking__user=request.user).select_related('booking__show__movie').order_by('-created_at')
        data = [{
            'id': p.id,
            'booking_reference': p.booking.booking_reference,
            'movie_title': p.booking.show.movie.title,
            'amount': str(p.amount),
            'currency': p.currency,
            'gateway': p.gateway,
            'payment_status': p.payment_status,
            'payment_method': p.payment_method,
            'transaction_id': p.transaction_id or 'N/A',
            'gateway_order_id': p.gateway_order_id or 'N/A',
            'failure_reason': p.failure_reason or '',
            'date': p.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for p in payments]
        return Response({'success': True, 'payments': data})


class PaymentDetailAPIView(APIView):
    """
    GET /api/v1/payments/<id_or_ref>/
    Returns payment detail for authorized user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk_or_ref):
        if pk_or_ref.isdigit():
            payment = Payment.objects.filter(pk=int(pk_or_ref), booking__user=request.user).select_related('booking__show__movie').first()
        else:
            payment = Payment.objects.filter(booking__booking_reference=pk_or_ref, booking__user=request.user).select_related('booking__show__movie').first()

        if not payment:
            return Response({'success': False, 'message': 'Payment record not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = {
            'id': payment.id,
            'booking_reference': payment.booking.booking_reference,
            'movie_title': payment.booking.show.movie.title,
            'amount': str(payment.amount),
            'currency': payment.currency,
            'gateway': payment.gateway,
            'payment_status': payment.payment_status,
            'payment_method': payment.payment_method,
            'transaction_id': payment.transaction_id or 'N/A',
            'gateway_order_id': payment.gateway_order_id or 'N/A',
            'failure_reason': payment.failure_reason or '',
            'webhook_verified': payment.webhook_verified,
            'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        return Response({'success': True, 'payment': data})


class UserBookingsAPIView(APIView):
    """
    GET /api/v1/bookings/history/ or /api/v1/bookings/my-bookings/
    Returns logged in user's complete booking history.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        release_expired_bookings()
        bookings = Booking.objects.filter(user=request.user).select_related('show__movie', 'show__theater', 'show__screen').prefetch_related('booked_seats__seat', 'payments').order_by('-created_at')
        return Response({'success': True, 'bookings': BookingDetailSerializer(bookings, many=True).data})


class BookingDetailAPIView(APIView):
    """
    GET /api/v1/bookings/<id_or_ref>/
    Returns detailed info for a single booking.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk_or_ref):
        release_expired_bookings()
        if str(pk_or_ref).isdigit():
            booking = Booking.objects.filter(pk=int(pk_or_ref), user=request.user).select_related('show__movie', 'show__theater', 'show__screen').prefetch_related('booked_seats__seat', 'payments').first()
        else:
            booking = Booking.objects.filter(booking_reference=pk_or_ref, user=request.user).select_related('show__movie', 'show__theater', 'show__screen').prefetch_related('booked_seats__seat', 'payments').first()

        if not booking:
            return Response({'success': False, 'message': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'success': True, 'booking': BookingDetailSerializer(booking).data})


class CancelBookingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_ref):
        try:
            refund = RefundService.process_cancellation_and_refund(booking_ref, request.user)
            return Response({
                'success': True,
                'message': f'Booking {booking_ref} cancelled. Refund initiated.',
                'refund_id': refund.refund_transaction_id
            })
        except ValueError as ve:
            return Response({'success': False, 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)


class HoldSeatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        show_id = request.data.get('show_id')
        seat_ids = request.data.get('seat_ids', [])

        if not show_id or not seat_ids:
            return Response({'success': False, 'message': 'show_id and seat_ids are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reservation = ReservationService.hold_seats(request.user, show_id, seat_ids)
            serializer = ReservationSerializer(reservation)
            return Response({
                'success': True,
                'message': 'Seats held successfully for 10 minutes.',
                'reservation': serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValueError as ve:
            return Response({'success': False, 'message': str(ve), 'code': 'SEAT_UNAVAILABLE'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ModifyReservationAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reservation_id = request.data.get('reservation_id')
        new_seat_ids = request.data.get('new_seat_ids', [])

        if not reservation_id or not new_seat_ids:
            return Response({'success': False, 'message': 'reservation_id and new_seat_ids required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reservation = ReservationService.modify_seats(request.user, reservation_id, new_seat_ids)
            return Response({
                'success': True,
                'message': 'Seat selection updated successfully.',
                'reservation': ReservationSerializer(reservation).data
            })
        except ValueError as ve:
            return Response({'success': False, 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)


class ReleaseReservationAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reservation_id = request.data.get('reservation_id')
        if not reservation_id:
            return Response({'success': False, 'message': 'reservation_id required.'}, status=status.HTTP_400_BAD_REQUEST)

        released = ReservationService.release_reservation(reservation_id, request.user)
        return Response({'success': released, 'message': 'Reservation released.' if released else 'Reservation not found.'})


class ReservationDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, reservation_id):
        res = Reservation.objects.filter(reservation_id=reservation_id, user=request.user).first()
        if not res:
            return Response({'success': False, 'message': 'Reservation not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'reservation': ReservationSerializer(res).data})


class CheckoutBookingAPIView(APIView):
    """
    Legacy reservation conversion checkout view compatibility alias.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reservation_id = request.data.get('reservation_id')
        payment_method = request.data.get('payment_method', Payment.Method.UPI)
        coupon_code = request.data.get('coupon_code')
        idempotency_key = request.data.get('idempotency_key')

        if not reservation_id:
            return Response({'success': False, 'message': 'reservation_id required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = BookingService.create_booking_from_reservation(
                reservation_id=reservation_id,
                user=request.user,
                payment_method=payment_method,
                coupon_code=coupon_code,
                idempotency_key=idempotency_key
            )
            return Response({
                'success': True,
                'message': 'Payment successful! Booking confirmed.',
                'booking': BookingDetailSerializer(booking).data
            }, status=status.HTTP_201_CREATED)
        except ValueError as ve:
            return Response({'success': False, 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidateCouponAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '').strip()
        amount_str = request.data.get('amount', '0.00')
        try:
            amount = Decimal(str(amount_str))
        except Exception:
            amount = Decimal('0.00')

        coupon = Coupon.objects.filter(code__iexact=code, is_active=True).first()
        if not coupon or not coupon.is_valid(amount):
            return Response({'success': False, 'message': 'Invalid or expired coupon code.'}, status=status.HTTP_400_BAD_REQUEST)

        discount = coupon.calculate_discount(amount)
        return Response({
            'success': True,
            'code': coupon.code,
            'discount_amount': str(discount),
            'final_amount': str(max(Decimal('0.00'), amount - discount))
        })


class AdminDashboardStatsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        now = timezone.now()
        today = now.date()

        confirmed_bookings = Booking.objects.filter(status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED])
        total_revenue = confirmed_bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        
        today_bookings = confirmed_bookings.filter(created_at__date=today)
        today_revenue = today_bookings.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        
        total_bookings_count = Booking.objects.count()
        today_bookings_count = today_bookings.count()
        active_users_count = User.objects.filter(is_active=True).count()

        total_seats = ShowSeat.objects.count()
        booked_seats = ShowSeat.objects.filter(status=ShowSeat.Status.BOOKED).count()
        occupancy_rate = round((booked_seats / total_seats * 100), 1) if total_seats > 0 else 0.0

        cancelled_count = Booking.objects.filter(status=Booking.Status.CANCELLED).count()
        cancellation_rate = round((cancelled_count / total_bookings_count * 100), 1) if total_bookings_count > 0 else 0.0

        successful_payments = Payment.objects.filter(payment_status=Payment.Status.SUCCESS).count()
        total_payments = Payment.objects.count()
        payment_success_rate = round((successful_payments / total_payments * 100), 1) if total_payments > 0 else 100.0

        seven_days_ago = today - timedelta(days=6)
        revenue_trends = []
        for i in range(7):
            day = seven_days_ago + timedelta(days=i)
            day_rev = Booking.objects.filter(
                status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
                created_at__date=day
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            revenue_trends.append({
                'date': day.strftime('%b %d'),
                'revenue': float(day_rev)
            })

        booking_trends = []
        for i in range(7):
            day = seven_days_ago + timedelta(days=i)
            day_count = Booking.objects.filter(created_at__date=day).count()
            booking_trends.append({
                'date': day.strftime('%b %d'),
                'bookings': day_count
            })

        top_movies = Movie.objects.annotate(
            rev=Sum('shows__bookings__total_amount', filter=Q(shows__bookings__status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]))
        ).order_by('-rev')[:5]

        top_movies_data = [
            {'title': m.title, 'revenue': float(m.rev or 0.0)} for m in top_movies
        ]

        return Response({
            'success': True,
            'kpis': {
                'total_revenue': float(total_revenue),
                'today_revenue': float(today_revenue),
                'total_bookings': total_bookings_count,
                'today_bookings': today_bookings_count,
                'active_users': active_users_count,
                'occupancy_rate': occupancy_rate,
                'cancellation_rate': cancellation_rate,
                'payment_success_rate': payment_success_rate,
            },
            'charts': {
                'revenue_trends': revenue_trends,
                'booking_trends': booking_trends,
                'top_movies': top_movies_data
            }
        })
