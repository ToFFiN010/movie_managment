import uuid
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from movies.models import Movie
from theaters.models import Theater, Screen, Seat

class ShowSchedule(models.Model):
    class Status(models.TextChoices):
        UPCOMING = 'UPCOMING', 'Upcoming'
        OPEN = 'OPEN', 'Booking Open'
        CLOSED = 'CLOSED', 'Booking Closed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='shows')
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='shows')
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='shows')
    show_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['show_date', 'start_time']
        indexes = [
            models.Index(fields=['movie']),
            models.Index(fields=['theater']),
            models.Index(fields=['screen']),
            models.Index(fields=['show_date']),
            models.Index(fields=['start_time']),
            models.Index(fields=['movie', 'show_date']),
            models.Index(fields=['theater', 'show_date']),
            models.Index(fields=['status', 'show_date']),
        ]

    def clean(self):
        super().clean()
        if self.screen and self.theater and self.screen.theater != self.theater:
            raise ValidationError({'screen': 'Selected screen does not belong to the selected theater.'})

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({'end_time': 'End time must be later than start time.'})

        # Overlap check
        if self.screen and self.show_date and self.start_time and self.end_time:
            overlapping = ShowSchedule.objects.filter(
                screen=self.screen,
                show_date=self.show_date,
                status__in=[self.Status.UPCOMING, self.Status.OPEN],
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError('Show schedule time overlaps with another show on the same screen.')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)
        if is_new:
            # Create ShowSeats automatically for the screen's seats
            seats = Seat.objects.filter(screen=self.screen, is_active=True)
            show_seats = [ShowSeat(show=self, seat=seat, status=ShowSeat.Status.AVAILABLE) for seat in seats]
            ShowSeat.objects.bulk_create(show_seats, ignore_conflicts=True)

    def __str__(self):
        return f"{self.movie.title} - {self.theater.name} ({self.screen.name}) on {self.show_date} at {self.start_time}"


class ShowSeat(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        RESERVED = 'RESERVED', 'Reserved'
        BOOKED = 'BOOKED', 'Booked'

    show = models.ForeignKey(ShowSchedule, on_delete=models.CASCADE, related_name='show_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='show_seats')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AVAILABLE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('show', 'seat')
        indexes = [
            models.Index(fields=['show', 'status']),
        ]

    def __str__(self):
        return f"{self.show.movie.title} - {self.show.show_date} - {self.seat.label}: {self.status}"


class Reservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'
        CONVERTED = 'CONVERTED', 'Converted'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    show = models.ForeignKey(ShowSchedule, on_delete=models.CASCADE, related_name='reservations')
    reservation_id = models.CharField(max_length=36, unique=True, editable=False)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'expires_at']),
        ]

    @property
    def is_valid(self):
        return self.status == self.Status.ACTIVE and timezone.now() < self.expires_at

    @property
    def remaining_seconds(self):
        if not self.is_valid:
            return 0
        diff = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(diff))

    def save(self, *args, **kwargs):
        if not self.reservation_id:
            self.reservation_id = f"RES-{uuid.uuid4().hex[:10].upper()}"
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reservation {self.reservation_id} - {self.user.username} ({self.status})"


class ReservationSeat(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='reserved_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='reservation_seats')
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ('reservation', 'seat')

    def __str__(self):
        return f"{self.reservation.reservation_id} - Seat {self.seat.label}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        EXPIRED = 'EXPIRED', 'Expired'
        COMPLETED = 'COMPLETED', 'Completed'

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    show = models.ForeignKey(ShowSchedule, on_delete=models.CASCADE, related_name='bookings')
    reservation = models.OneToOneField(Reservation, on_delete=models.SET_NULL, null=True, blank=True, related_name='booking')
    booking_reference = models.CharField(max_length=32, unique=True, editable=False)
    booking_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    coupon_code = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=15, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    reservation_expires_at = models.DateTimeField(null=True, blank=True)
    qr_code_path = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_expired(self):
        if self.status == self.Status.PENDING and self.reservation_expires_at:
            return timezone.now() > self.reservation_expires_at
        return self.status == self.Status.EXPIRED

    @property
    def payment(self):
        return self.payments.order_by('-created_at').first()

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = f"CP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.booking_reference} - {self.user.username} ({self.status})"


class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='bookings')
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ('booking', 'seat')

    def __str__(self):
        return f"{self.booking.booking_reference} - Seat {self.seat.label}"


class Payment(models.Model):
    class Gateway(models.TextChoices):
        RAZORPAY = 'RAZORPAY', 'Razorpay'
        MOCK = 'MOCK', 'Mock Gateway'

    class Method(models.TextChoices):
        UPI = 'UPI', 'UPI'
        CREDIT_CARD = 'CREDIT_CARD', 'Credit Card'
        DEBIT_CARD = 'DEBIT_CARD', 'Debit Card'
        NET_BANKING = 'NET_BANKING', 'Net Banking'
        WALLET = 'WALLET', 'Wallet'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REFUNDED = 'REFUNDED', 'Refunded'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.RAZORPAY)
    gateway_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=Method.choices, default=Method.UPI)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    payment_status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    signature = models.CharField(max_length=255, blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    webhook_verified = models.BooleanField(default=False)
    idempotency_key = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.transaction_id or self.gateway_order_id or self.id} for Booking {self.booking.booking_reference}"



class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
        FLAT = 'FLAT', 'Flat Amount'

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=15, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    min_booking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self, booking_amount):
        now = timezone.now()
        if not self.is_active or now < self.valid_from or now > self.valid_to:
            return False
        if booking_amount < self.min_booking_amount:
            return False
        return True

    def calculate_discount(self, booking_amount):
        if not self.is_valid(booking_amount):
            return Decimal('0.00')
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = (booking_amount * self.discount_value) / Decimal('100.0')
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount.quantize(Decimal('0.01'))
        else:
            return min(self.discount_value, booking_amount).quantize(Decimal('0.01'))

    def __str__(self):
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == self.DiscountType.PERCENTAGE else ' OFF'})"


class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        PROCESSED = 'PROCESSED', 'Processed'
        REJECTED = 'REJECTED', 'Rejected'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='refunds')
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    refund_transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.refund_transaction_id:
            self.refund_transaction_id = f"REF-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Refund {self.refund_transaction_id} for Booking {self.booking.booking_reference}"


class Ticket(models.Model):
    class EmailStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='ticket')
    ticket_number = models.CharField(max_length=40, unique=True, editable=False)
    qr_token = models.CharField(max_length=64, unique=True, editable=False)
    pdf_file = models.FileField(upload_to='tickets/%Y/%m/', blank=True, null=True)
    qr_code_image = models.ImageField(upload_to='tickets/qr/%Y/%m/', blank=True, null=True)

    email_status = models.CharField(max_length=15, choices=EmailStatus.choices, default=EmailStatus.PENDING)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_attempts = models.PositiveIntegerField(default=0)
    last_email_error = models.TextField(blank=True, null=True)

    generated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = f"CINE-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if not self.qr_token:
            self.qr_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket {self.ticket_number} for {self.booking.booking_reference}"

