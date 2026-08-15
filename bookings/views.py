from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import ShowSchedule, Booking, BookingSeat, Payment
from theaters.models import Seat, Theater
from movies.models import Movie
from notifications.models import Notification
from .utils import generate_ticket_pdf

CONVENIENCE_FEE_PER_TICKET = Decimal('2.50')

@login_required
def show_seat_selection_view(request, show_id):
    show = get_object_or_404(ShowSchedule.objects.select_related('movie', 'theater', 'screen'), pk=show_id)

    # Fetch all seats for the screen
    seats = Seat.objects.filter(screen=show.screen, is_active=True).order_by('row', 'seat_number')

    # Fetch already booked seat IDs for this show (where booking status is PENDING or CONFIRMED)
    booked_seat_ids = set(BookingSeat.objects.filter(
        booking__show=show,
        booking__status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.COMPLETED]
    ).values_list('seat_id', flat=True))

    # Group seats by row for grid display
    seat_grid = {}
    for seat in seats:
        seat_status = 'BOOKED' if seat.id in booked_seat_ids else 'AVAILABLE'
        ticket_cost = (show.ticket_price * seat.price_multiplier).quantize(Decimal('0.01'))
        
        seat_data = {
            'id': seat.id,
            'number': seat.seat_number,
            'label': seat.label,
            'seat_type': seat.seat_type,
            'status': seat_status,
            'price': str(ticket_cost)
        }
        seat_grid.setdefault(seat.row, []).append(seat_data)

    context = {
        'show': show,
        'seat_grid': seat_grid,
        'base_price': show.ticket_price,
        'convenience_fee': CONVENIENCE_FEE_PER_TICKET,
    }
    return render(request, 'bookings/seat_selection.html', context)


@login_required
def create_booking_view(request, show_id):
    """
    Handles form submission from seat selection to create a pending booking atomically.
    Prevents double-booking using select_for_update and database transactions.
    """
    if request.method != 'POST':
        return redirect('bookings:seat_selection', show_id=show_id)

    seat_ids_str = request.POST.get('selected_seats', '')
    if not seat_ids_str:
        messages.error(request, 'Please select at least one seat to proceed.')
        return redirect('bookings:seat_selection', show_id=show_id)

    selected_seat_ids = [int(s) for s in seat_ids_str.split(',') if s.strip().isdigit()]
    if not selected_seat_ids:
        messages.error(request, 'Invalid seat selection.')
        return redirect('bookings:seat_selection', show_id=show_id)

    try:
        with transaction.atomic():
            show = ShowSchedule.objects.select_for_update().get(pk=show_id)

            # Check if any selected seat is already booked concurrently
            already_booked = BookingSeat.objects.filter(
                booking__show=show,
                booking__status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
                seat_id__in=selected_seat_ids
            ).exists()

            if already_booked:
                messages.error(request, 'One or more selected seats have already been booked by another user. Please choose available seats.')
                return redirect('bookings:seat_selection', show_id=show_id)

            # Fetch seats
            seats = Seat.objects.filter(id__in=selected_seat_ids, screen=show.screen)
            if len(seats) != len(selected_seat_ids):
                messages.error(request, 'Some selected seats are invalid.')
                return redirect('bookings:seat_selection', show_id=show_id)

            # Calculate total amount
            subtotal = Decimal('0.00')
            seat_price_tuples = []
            for seat in seats:
                seat_cost = (show.ticket_price * seat.price_multiplier).quantize(Decimal('0.01'))
                subtotal += seat_cost
                seat_price_tuples.append((seat, seat_cost))

            total_convenience_fee = CONVENIENCE_FEE_PER_TICKET * len(seats)
            grand_total = subtotal + total_convenience_fee

            # Create Booking
            booking = Booking.objects.create(
                user=request.user,
                show=show,
                total_amount=grand_total,
                status=Booking.Status.PENDING,
                payment_status=Booking.PaymentStatus.PENDING
            )

            # Create BookingSeat entries
            for seat, price in seat_price_tuples:
                BookingSeat.objects.create(
                    booking=booking,
                    seat=seat,
                    price=price
                )

            return redirect('bookings:checkout', booking_ref=booking.booking_reference)

    except Exception as e:
        messages.error(request, f"An error occurred while creating your booking: {str(e)}")
        return redirect('bookings:seat_selection', show_id=show_id)


@login_required
def booking_checkout_view(request, booking_ref):
    booking = get_object_or_404(
        Booking.objects.select_related('show__movie', 'show__theater', 'show__screen').prefetch_related('booked_seats__seat'),
        booking_reference=booking_ref,
        user=request.user
    )

    if booking.status == Booking.Status.CONFIRMED:
        return redirect('bookings:confirmation', booking_ref=booking.booking_reference)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', Payment.Method.UPI)
        
        # Process Mock Payment Gateway Transaction
        with transaction.atomic():
            booking.status = Booking.Status.CONFIRMED
            booking.payment_status = Booking.PaymentStatus.PAID
            booking.save()

            txn_id = f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{booking.id}"
            Payment.objects.create(
                booking=booking,
                transaction_id=txn_id,
                payment_method=payment_method,
                amount=booking.total_amount,
                payment_status=Payment.Status.SUCCESS
            )

            # Send Notification to User
            Notification.objects.create(
                user=request.user,
                title="Booking Confirmed!",
                message=f"Your ticket for '{booking.show.movie.title}' at {booking.show.theater.name} (Ref: {booking.booking_reference}) is confirmed.",
                notification_type=Notification.Type.BOOKING
            )

        messages.success(request, 'Payment successful! Your tickets are confirmed.')
        return redirect('bookings:confirmation', booking_ref=booking.booking_reference)

    context = {
        'booking': booking,
        'seats': booking.booked_seats.all(),
        'razorpay_key_id': 'rzp_test_samplekey123',
    }
    return render(request, 'bookings/checkout.html', context)


@login_required
def booking_confirmation_view(request, booking_ref):
    booking = get_object_or_404(
        Booking.objects.select_related('show__movie', 'show__theater', 'show__screen').prefetch_related('booked_seats__seat'),
        booking_reference=booking_ref,
        user=request.user
    )
    return render(request, 'bookings/confirmation.html', {'booking': booking})


@login_required
def download_ticket_pdf_view(request, booking_ref):
    booking = get_object_or_404(
        Booking.objects.select_related('show__movie', 'show__theater', 'show__screen').prefetch_related('booked_seats__seat'),
        booking_reference=booking_ref,
        user=request.user
    )
    pdf_buffer = generate_ticket_pdf(booking)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{booking.booking_reference}.pdf"'
    return response


@login_required
def user_bookings_view(request):
    bookings = Booking.objects.filter(user=request.user).select_related('show__movie', 'show__theater', 'show__screen').order_by('-created_at')
    return render(request, 'bookings/my_bookings.html', {'bookings': bookings})


@login_required
def cancel_booking_view(request, booking_ref):
    booking = get_object_or_404(Booking, booking_reference=booking_ref, user=request.user)

    if booking.status in [Booking.Status.CANCELLED, Booking.Status.COMPLETED]:
        messages.error(request, 'This booking cannot be cancelled.')
        return redirect('bookings:my_bookings')

    if request.method == 'POST':
        with transaction.atomic():
            booking.status = Booking.Status.CANCELLED
            booking.payment_status = Booking.PaymentStatus.REFUNDED
            booking.save()

            if hasattr(booking, 'payment'):
                booking.payment.payment_status = Payment.Status.FAILED
                booking.payment.save()

            Notification.objects.create(
                user=request.user,
                title="Booking Cancelled",
                message=f"Booking {booking.booking_reference} for '{booking.show.movie.title}' has been cancelled. Refund initiated.",
                notification_type=Notification.Type.CANCELLATION
            )

        messages.success(request, f'Booking {booking.booking_reference} cancelled successfully.')
        return redirect('bookings:my_bookings')

    return render(request, 'bookings/cancel_confirm.html', {'booking': booking})


def booking_movie_view(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    shows = ShowSchedule.objects.filter(
        movie=movie,
        status=ShowSchedule.Status.OPEN
    ).select_related('theater', 'screen').order_by('show_date', 'start_time')

    theaters = Theater.objects.filter(shows__in=shows).distinct()

    selected_theater_id = request.GET.get('theater_id')
    if selected_theater_id:
        try:
            selected_theater_id = int(selected_theater_id)
        except ValueError:
            selected_theater_id = None

    if not selected_theater_id and theaters.exists():
        selected_theater_id = theaters.first().id

    selected_theater = None
    if selected_theater_id:
        selected_theater = theaters.filter(id=selected_theater_id).first()

    theater_shows = shows.filter(theater_id=selected_theater_id) if selected_theater_id else shows

    dates = theater_shows.values_list('show_date', flat=True).distinct()

    selected_date_str = request.GET.get('date')
    selected_date = None
    if selected_date_str:
        try:
            selected_date = timezone.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = None

    if not selected_date and dates.exists():
        selected_date = dates.first()

    available_shows = theater_shows.filter(show_date=selected_date) if selected_date else theater_shows

    context = {
        'movie': movie,
        'theaters': theaters,
        'selected_theater': selected_theater,
        'selected_theater_id': selected_theater_id,
        'dates': dates,
        'selected_date': selected_date,
        'available_shows': available_shows,
    }
    return render(request, 'bookings/booking_movie.html', context)


def api_get_theaters(request):
    movie_id = request.GET.get('movie_id')
    if not movie_id:
        return JsonResponse({'theaters': []})

    shows = ShowSchedule.objects.filter(movie_id=movie_id, status=ShowSchedule.Status.OPEN)
    theaters = Theater.objects.filter(shows__in=shows).distinct()
    data = [{'id': t.id, 'name': t.name, 'city': t.city} for t in theaters]
    return JsonResponse({'theaters': data})


def api_get_dates(request):
    movie_id = request.GET.get('movie_id')
    theater_id = request.GET.get('theater_id')
    if not movie_id or not theater_id:
        return JsonResponse({'dates': []})

    shows = ShowSchedule.objects.filter(movie_id=movie_id, theater_id=theater_id, status=ShowSchedule.Status.OPEN)
    dates = shows.values_list('show_date', flat=True).distinct().order_by('show_date')
    data = [{'date_str': d.strftime('%Y-%m-%d'), 'formatted_date': d.strftime('%a, %d %b %Y')} for d in dates]
    return JsonResponse({'dates': data})


def api_get_shows(request):
    movie_id = request.GET.get('movie_id')
    theater_id = request.GET.get('theater_id')
    date_str = request.GET.get('date')
    if not movie_id or not theater_id or not date_str:
        return JsonResponse({'shows': []})

    shows = ShowSchedule.objects.filter(
        movie_id=movie_id,
        theater_id=theater_id,
        show_date=date_str,
        status=ShowSchedule.Status.OPEN
    ).select_related('screen').order_by('start_time')

    data = [{
        'id': s.id,
        'time_str': s.start_time.strftime('%I:%M %p'),
        'screen': s.screen.name,
        'price': str(s.ticket_price)
    } for s in shows]

    return JsonResponse({'shows': data})


