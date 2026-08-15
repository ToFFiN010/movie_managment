import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
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

    class Meta:
        ordering = ['show_date', 'start_time']

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
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movie.title} - {self.theater.name} ({self.screen.name}) on {self.show_date} at {self.start_time}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    show = models.ForeignKey(ShowSchedule, on_delete=models.CASCADE, related_name='bookings')
    booking_reference = models.CharField(max_length=32, unique=True, editable=False)
    booking_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=15, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = f"BK-{uuid.uuid4().hex[:10].upper()}"
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
    class Method(models.TextChoices):
        UPI = 'UPI', 'UPI'
        CREDIT_CARD = 'CREDIT_CARD', 'Credit Card'
        DEBIT_CARD = 'DEBIT_CARD', 'Debit Card'
        NET_BANKING = 'NET_BANKING', 'Net Banking'
        WALLET = 'WALLET', 'Wallet'

    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        PENDING = 'PENDING', 'Pending'

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=20, choices=Method.choices, default=Method.UPI)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} for Booking {self.booking.booking_reference}"
