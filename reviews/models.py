from django.db import models
from django.conf import settings
from django.db.models import Avg, Count
from movies.models import Movie
from bookings.models import Booking

class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        HIDDEN = 'HIDDEN', 'Hidden'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='review')
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    review_text = models.TextField()
    is_verified_viewer = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.APPROVED)
    report_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'movie')
        ordering = ['-created_at']

    def update_movie_rating(self):
        approved_reviews = Review.objects.filter(movie=self.movie, status=Review.Status.APPROVED)
        total = approved_reviews.count()
        avg = approved_reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
        
        self.movie.total_reviews = total
        self.movie.average_rating = round(avg, 1)
        self.movie.save(update_fields=['total_reviews', 'average_rating'])

    def save(self, *args, **kwargs):
        # Auto-detect verified viewer badge from completed booking
        if not self.is_verified_viewer:
            completed_booking_exists = Booking.objects.filter(
                user=self.user,
                show__movie=self.movie,
                status__in=[Booking.Status.COMPLETED, Booking.Status.CONFIRMED],
                payment_status=Booking.PaymentStatus.PAID
            ).exists()
            if completed_booking_exists:
                self.is_verified_viewer = True

        super().save(*args, **kwargs)
        self.update_movie_rating()

    def delete(self, *args, **kwargs):
        movie = self.movie
        super().delete(*args, **kwargs)
        # Update movie stats after deletion
        approved_reviews = Review.objects.filter(movie=movie, status=Review.Status.APPROVED)
        total = approved_reviews.count()
        avg = approved_reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
        movie.total_reviews = total
        movie.average_rating = round(avg, 1)
        movie.save(update_fields=['total_reviews', 'average_rating'])

    def __str__(self):
        return f"{self.user.username} - {self.movie.title} ({self.rating}★)"


class ReviewReport(models.Model):
    class Reason(models.TextChoices):
        SPAM = 'Spam', 'Spam'
        OFFENSIVE = 'Offensive content', 'Offensive Content'
        HARASSMENT = 'Harassment', 'Harassment'
        FAKE = 'Fake review', 'Fake Review'
        INAPPROPRIATE = 'Inappropriate content', 'Inappropriate Content'
        OTHER = 'Other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RESOLVED = 'RESOLVED', 'Resolved'
        IGNORED = 'IGNORED', 'Ignored'

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_reports')
    reason = models.CharField(max_length=30, choices=Reason.choices, default=Reason.SPAM)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'reported_by')
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.review.report_count = self.review.reports.count()
            if self.review.report_count >= 3 and self.review.status == Review.Status.APPROVED:
                self.review.status = Review.Status.HIDDEN
            self.review.save(update_fields=['report_count', 'status'])

    def __str__(self):
        return f"Report on {self.review} by {self.reported_by.username}"
