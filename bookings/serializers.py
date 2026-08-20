from rest_framework import serializers
from bookings.models import (
    ShowSchedule, ShowSeat, Reservation, ReservationSeat,
    Booking, BookingSeat, Payment, Coupon, Refund
)
from theaters.models import Seat
from accounts.models import User, AuditLog


class SeatSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)

    class Meta:
        model = Seat
        fields = ['id', 'row', 'seat_number', 'seat_type', 'price_multiplier', 'is_active', 'label']


class ShowSeatSerializer(serializers.ModelSerializer):
    seat = SeatSerializer(read_only=True)

    class Meta:
        model = ShowSeat
        fields = ['id', 'show', 'seat', 'status', 'updated_at']


class ReservationSeatSerializer(serializers.ModelSerializer):
    seat = SeatSerializer(read_only=True)

    class Meta:
        model = ReservationSeat
        fields = ['id', 'seat', 'price']


class ReservationSerializer(serializers.ModelSerializer):
    reserved_seats = ReservationSeatSerializer(many=True, read_only=True)
    remaining_seconds = serializers.IntegerField(read_only=True)
    movie_title = serializers.CharField(source='show.movie.title', read_only=True)
    theater_name = serializers.CharField(source='show.theater.name', read_only=True)
    show_time = serializers.TimeField(source='show.start_time', read_only=True)
    show_date = serializers.DateField(source='show.show_date', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'reservation_id', 'user', 'show', 'status', 'total_amount',
            'created_at', 'expires_at', 'remaining_seconds', 'reserved_seats',
            'movie_title', 'theater_name', 'show_time', 'show_date'
        ]


class BookingSeatSerializer(serializers.ModelSerializer):
    seat = SeatSerializer(read_only=True)

    class Meta:
        model = BookingSeat
        fields = ['id', 'seat', 'price']


class BookingDetailSerializer(serializers.ModelSerializer):
    booked_seats = BookingSeatSerializer(many=True, read_only=True)
    movie_title = serializers.CharField(source='show.movie.title', read_only=True)
    movie_poster = serializers.CharField(source='show.movie.get_poster_url', read_only=True)
    theater_name = serializers.CharField(source='show.theater.name', read_only=True)
    screen_name = serializers.CharField(source='show.screen.name', read_only=True)
    show_date = serializers.DateField(source='show.show_date', read_only=True)
    start_time = serializers.TimeField(source='show.start_time', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'show', 'movie_title', 'movie_poster',
            'theater_name', 'screen_name', 'show_date', 'start_time',
            'total_amount', 'discount_amount', 'coupon_code', 'status',
            'payment_status', 'qr_code_path', 'booked_seats', 'created_at'
        ]


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'


class RefundSerializer(serializers.ModelSerializer):
    booking_reference = serializers.CharField(source='booking.booking_reference', read_only=True)

    class Meta:
        model = Refund
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='System')

    class Meta:
        model = AuditLog
        fields = '__all__'
