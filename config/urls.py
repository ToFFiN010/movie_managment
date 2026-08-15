from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .dashboard_views import custom_admin_dashboard
from movies.api_views import (
    MovieListAPIView, MovieDetailAPIView, trending_movies_api,
    recent_movies_api, similar_movies_api, GenreListAPIView,
    LanguageListAPIView, TheaterListAPIView, ShowScheduleListAPIView,
    BookingListCreateAPIView, ReviewListCreateAPIView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/admin/', custom_admin_dashboard, name='custom_admin_dashboard'),

    # HTML Web Apps
    path('accounts/', include('accounts.urls')),
    path('theaters/', include('theaters.urls')),
    path('bookings/', include('bookings.urls')),
    path('reviews/', include('reviews.urls')),
    path('notifications/', include('notifications.urls')),
    path('', include('movies.urls')),

    # REST API endpoints
    path('api/movies/', MovieListAPIView.as_view(), name='api_movie_list'),
    path('api/movies/<int:pk>/', MovieDetailAPIView.as_view(), name='api_movie_detail'),
    path('api/movies/trending/', trending_movies_api, name='api_movie_trending'),
    path('api/movies/recent/', recent_movies_api, name='api_movie_recent'),
    path('api/movies/similar/<int:pk>/', similar_movies_api, name='api_movie_similar'),
    path('api/genres/', GenreListAPIView.as_view(), name='api_genre_list'),
    path('api/languages/', LanguageListAPIView.as_view(), name='api_language_list'),
    path('api/theaters/', TheaterListAPIView.as_view(), name='api_theater_list'),
    path('api/shows/', ShowScheduleListAPIView.as_view(), name='api_show_list'),
    path('api/bookings/', BookingListCreateAPIView.as_view(), name='api_booking_list'),
    path('api/reviews/', ReviewListCreateAPIView.as_view(), name='api_review_list'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
