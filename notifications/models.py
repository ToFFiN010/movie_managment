from django.db import models
from django.conf import settings

class Notification(models.Model):
    class Type(models.TextChoices):
        BOOKING = 'BOOKING', 'Booking Confirmation'
        PAYMENT = 'PAYMENT', 'Payment Update'
        CANCELLATION = 'CANCELLATION', 'Booking Cancellation'
        SHOW_REMINDER = 'SHOW_REMINDER', 'Show Reminder'
        RELEASE = 'RELEASE', 'Movie Release Alert'
        REVIEW = 'REVIEW', 'Review Moderation'
        GENERAL = 'GENERAL', 'General Notification'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.GENERAL)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
