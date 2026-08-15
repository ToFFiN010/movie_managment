from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from movies.models import Movie, Genre
from bookings.models import Booking, ShowSchedule, Payment
from reviews.models import Review, ReviewReport
from accounts.models import User

def is_admin(user):
    return user.is_authenticated and (user.role == User.Role.ADMIN or user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_admin)
def custom_admin_dashboard(request):
    today = timezone.now().date()

    total_movies = Movie.objects.count()
    now_showing_count = Movie.objects.filter(status=Movie.Status.NOW_SHOWING).count()
    upcoming_count = Movie.objects.filter(status=Movie.Status.UPCOMING).count()
    total_users = User.objects.count()
    
    total_bookings = Booking.objects.count()
    todays_bookings = Booking.objects.filter(created_at__date=today).count()
    
    confirmed_bookings = Booking.objects.filter(payment_status=Booking.PaymentStatus.PAID)
    total_revenue = confirmed_bookings.aggregate(total=Sum('total_amount'))['total'] or 0.0

    total_reviews = Review.objects.count()
    avg_rating = Movie.objects.filter(status=Movie.Status.NOW_SHOWING).aggregate(avg=Avg('average_rating'))['avg'] or 0.0

    # Top popular movies by booking count
    popular_movies = Movie.objects.annotate(
        booking_count=Count('shows__bookings', filter=Q(shows__bookings__status=Booking.Status.CONFIRMED))
    ).order_by('-booking_count')[:5]

    # Rating distribution breakdown
    rating_counts = list(Review.objects.values('rating').annotate(count=Count('id')).order_by('rating'))

    # Review reports pending
    pending_reports = ReviewReport.objects.filter(status=ReviewReport.Status.PENDING).select_related('review', 'reported_by')[:10]

    context = {
        'total_movies': total_movies,
        'now_showing_count': now_showing_count,
        'upcoming_count': upcoming_count,
        'total_users': total_users,
        'total_bookings': total_bookings,
        'todays_bookings': todays_bookings,
        'total_revenue': total_revenue,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'popular_movies': popular_movies,
        'rating_counts': rating_counts,
        'pending_reports': pending_reports,
    }
    return render(request, 'admin_custom/dashboard.html', context)
