from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .dashboard_views import (
    custom_admin_dashboard, admin_movie_images_audit_view,
    admin_movie_trailers_audit_view, admin_movie_image_status_view,
    admin_movie_media_health_view
)
from movies.api_views import (
    MovieListAPIView, MovieDetailAPIView, trending_movies_api,
    recent_movies_api, similar_movies_api, GenreListAPIView,
    LanguageListAPIView, TheaterListAPIView, ShowScheduleListAPIView,
    BookingListCreateAPIView, ReviewListCreateAPIView
)

from bookings.api_views import (
    ShowSeatLayoutAPIView, HoldSeatsAPIView, ModifyReservationAPIView,
    ReleaseReservationAPIView, ReservationDetailAPIView, CheckoutBookingAPIView,
    UserBookingsAPIView, CancelBookingAPIView, PaymentWebhookAPIView,
    ValidateCouponAPIView, AdminDashboardStatsAPIView,
    CreateBookingOrderAPIView, VerifyPaymentAPIView, RetryPaymentAPIView,
    CancelPaymentAPIView, PaymentHistoryAPIView, PaymentDetailAPIView,
    BookingDetailAPIView
)

from bookings import views as booking_views

urlpatterns = [
    path('admin/movie-media/', admin_movie_media_health_view, name='admin_movie_media_health'),
    path('admin/movie-image-status/', admin_movie_image_status_view, name='admin_movie_image_status'),
    path('admin/movie-images/', admin_movie_images_audit_view, name='admin_movie_images_audit'),
    path('admin/movie-trailers/', admin_movie_trailers_audit_view, name='admin_movie_trailers_audit'),
    path('admin/', admin.site.urls),
    path('dashboard/admin/', custom_admin_dashboard, name='custom_admin_dashboard'),

    # HTML Web Apps
    path('accounts/', include('accounts.urls')),
    path('theaters/', include('theaters.urls')),
    path('bookings/', include('bookings.urls')),
    path('reviews/', include('reviews.urls')),
    path('notifications/', include('notifications.urls')),
    path('tickets/verify/<str:qr_token>/', booking_views.verify_ticket_view, name='root_verify_ticket'),
    path('', include('movies.urls')),

    # REST API v1 endpoints
    path('api/v1/movies/', MovieListAPIView.as_view(), name='api_v1_movie_list'),
    path('api/v1/movies/<int:pk>/', MovieDetailAPIView.as_view(), name='api_v1_movie_detail'),
    path('api/v1/movies/trending/', trending_movies_api, name='api_v1_movie_trending'),
    path('api/v1/movies/recent/', recent_movies_api, name='api_v1_movie_recent'),
    path('api/v1/movies/similar/<int:pk>/', similar_movies_api, name='api_v1_movie_similar'),
    path('api/v1/genres/', GenreListAPIView.as_view(), name='api_v1_genre_list'),
    path('api/v1/languages/', LanguageListAPIView.as_view(), name='api_v1_language_list'),
    path('api/v1/theaters/', TheaterListAPIView.as_view(), name='api_v1_theater_list'),
    path('api/v1/shows/', ShowScheduleListAPIView.as_view(), name='api_v1_show_list'),
    path('api/v1/seats/<int:show_id>/', ShowSeatLayoutAPIView.as_view(), name='api_v1_seat_layout'),
    
    # Reservation & Booking REST APIs
    path('api/v1/reservations/hold/', HoldSeatsAPIView.as_view(), name='api_v1_reservation_hold'),
    path('api/v1/reservations/modify/', ModifyReservationAPIView.as_view(), name='api_v1_reservation_modify'),
    path('api/v1/reservations/release/', ReleaseReservationAPIView.as_view(), name='api_v1_reservation_release'),
    path('api/v1/reservations/<str:reservation_id>/', ReservationDetailAPIView.as_view(), name='api_v1_reservation_detail'),
    path('api/v1/bookings/create/', CreateBookingOrderAPIView.as_view(), name='api_v1_booking_create'),
    path('api/v1/bookings/checkout/', CheckoutBookingAPIView.as_view(), name='api_v1_booking_checkout'),
    path('api/v1/bookings/history/', UserBookingsAPIView.as_view(), name='api_v1_booking_history'),
    path('api/v1/bookings/my-bookings/', UserBookingsAPIView.as_view(), name='api_v1_user_bookings'),
    path('api/v1/bookings/<str:booking_ref>/cancel/', CancelBookingAPIView.as_view(), name='api_v1_booking_cancel'),
    path('api/v1/bookings/<str:pk_or_ref>/', BookingDetailAPIView.as_view(), name='api_v1_booking_detail'),
    
    # Razorpay Payment Gateway REST APIs
    path('api/v1/payments/create-order/', CreateBookingOrderAPIView.as_view(), name='api_v1_payment_create_order'),
    path('api/v1/payments/verify/', VerifyPaymentAPIView.as_view(), name='api_v1_payment_verify'),
    path('api/v1/payments/webhook/', PaymentWebhookAPIView.as_view(), name='api_v1_payment_webhook'),
    path('api/v1/payments/history/', PaymentHistoryAPIView.as_view(), name='api_v1_payment_history'),
    path('api/v1/payments/<str:pk_or_ref>/retry/', RetryPaymentAPIView.as_view(), name='api_v1_payment_retry'),
    path('api/v1/payments/<str:pk_or_ref>/cancel/', CancelPaymentAPIView.as_view(), name='api_v1_payment_cancel'),
    path('api/v1/payments/<str:pk_or_ref>/', PaymentDetailAPIView.as_view(), name='api_v1_payment_detail'),

    # Auxiliary APIs
    path('api/v1/coupons/validate/', ValidateCouponAPIView.as_view(), name='api_v1_coupon_validate'),
    path('api/v1/reviews/', ReviewListCreateAPIView.as_view(), name='api_v1_review_list'),
    path('api/v1/admin/stats/', AdminDashboardStatsAPIView.as_view(), name='api_v1_admin_stats'),

    # Standard Section 25 Root API Aliases
    path('api/bookings/create/', CreateBookingOrderAPIView.as_view()),
    path('api/bookings/history/', UserBookingsAPIView.as_view()),
    path('api/bookings/<str:booking_ref>/cancel/', CancelBookingAPIView.as_view()),
    path('api/bookings/<str:pk_or_ref>/', BookingDetailAPIView.as_view()),
    path('api/payments/create-order/', CreateBookingOrderAPIView.as_view()),
    path('api/payments/verify/', VerifyPaymentAPIView.as_view()),
    path('api/payments/webhook/', PaymentWebhookAPIView.as_view()),
    path('api/payments/history/', PaymentHistoryAPIView.as_view()),
    path('api/payments/<str:pk_or_ref>/retry/', RetryPaymentAPIView.as_view()),
    path('api/payments/<str:pk_or_ref>/cancel/', CancelPaymentAPIView.as_view()),
    path('api/payments/<str:pk_or_ref>/', PaymentDetailAPIView.as_view()),
    path('api/movies/', MovieListAPIView.as_view()),
    path('api/shows/', ShowScheduleListAPIView.as_view()),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
