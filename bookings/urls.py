from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('movie/<int:movie_id>/', views.booking_movie_view, name='booking_movie'),
    path('my-bookings/', views.user_bookings_view, name='my_bookings'),
    path('seats/<int:show_id>/', views.show_seat_selection_view, name='seat_selection'),
    path('create/<int:show_id>/', views.create_booking_view, name='create_booking'),
    path('checkout/<str:booking_ref>/', views.booking_checkout_view, name='checkout'),
    path('confirmation/<str:booking_ref>/', views.booking_confirmation_view, name='confirmation'),
    path('ticket/<str:booking_ref>/pdf/', views.download_ticket_pdf_view, name='download_ticket'),
    path('tickets/verify/<str:qr_token>/', views.verify_ticket_view, name='verify_ticket'),
    path('cancel/<str:booking_ref>/', views.cancel_booking_view, name='cancel_booking'),

    # Quick Booking Dynamic API Routes
    path('api/theaters/', views.api_get_theaters, name='api_theaters'),
    path('api/dates/', views.api_get_dates, name='api_dates'),
    path('api/shows/', views.api_get_shows, name='api_shows'),
]

