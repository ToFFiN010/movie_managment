from .models import Notification

def unread_notifications(request):
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        count = Notification.objects.filter(user=user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
