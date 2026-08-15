from django.db import models

class Theater(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'

    name = models.CharField(max_length=150)
    location = models.CharField(max_length=150)
    address = models.TextField()
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    facilities = models.CharField(max_length=255, help_text="Comma-separated e.g. Parking, Food Court, Dolby Atmos", blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['city', 'name']

    def __str__(self):
        return f"{self.name} ({self.city})"


class Screen(models.Model):
    class ScreenType(models.TextChoices):
        TWO_D = '2D', '2D'
        THREE_D = '3D', '3D'
        IMAX = 'IMAX', 'IMAX'
        FOUR_DX = '4DX', '4DX'

    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='screens')
    name = models.CharField(max_length=50)
    screen_number = models.PositiveIntegerField()
    capacity = models.PositiveIntegerField(default=50)
    screen_type = models.CharField(max_length=10, choices=ScreenType.choices, default=ScreenType.TWO_D)

    class Meta:
        unique_together = ('theater', 'screen_number')
        ordering = ['theater', 'screen_number']

    def __str__(self):
        return f"{self.theater.name} - {self.name} ({self.screen_type})"

    def generate_seats(self):
        """Automatically generates layout grid of seats if not already created."""
        if self.seats.exists():
            return
        
        rows = ['A', 'B', 'C', 'D', 'E', 'F']
        seats_per_row = max(1, self.capacity // len(rows))
        
        for idx, row in enumerate(rows):
            if idx < 3:
                seat_type = Seat.SeatType.REGULAR
                multiplier = 1.0
            elif idx < 5:
                seat_type = Seat.SeatType.PREMIUM
                multiplier = 1.25
            else:
                seat_type = Seat.SeatType.RECLINER
                multiplier = 1.60

            for num in range(1, seats_per_row + 1):
                Seat.objects.create(
                    screen=self,
                    row=row,
                    seat_number=num,
                    seat_type=seat_type,
                    price_multiplier=multiplier,
                    is_active=True
                )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.generate_seats()


class Seat(models.Model):
    class SeatType(models.TextChoices):
        REGULAR = 'Regular', 'Regular'
        PREMIUM = 'Premium', 'Premium'
        RECLINER = 'Recliner', 'Recliner'

    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='seats')
    row = models.CharField(max_length=5)
    seat_number = models.PositiveIntegerField()
    seat_type = models.CharField(max_length=20, choices=SeatType.choices, default=SeatType.REGULAR)
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('screen', 'row', 'seat_number')
        ordering = ['row', 'seat_number']

    @property
    def label(self):
        return f"{self.row}{self.seat_number}"

    def __str__(self):
        return f"{self.screen} - Seat {self.label} ({self.seat_type})"
