from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Review, ReviewReport
from .forms import ReviewForm, ReviewReportForm
from movies.models import Movie
from bookings.models import Booking

@login_required
def create_review_view(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)

    # Strict Eligibility Check: Must have a paid/completed booking for this movie
    user_booking = Booking.objects.filter(
        user=request.user,
        show__movie=movie,
        status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
        payment_status=Booking.PaymentStatus.PAID
    ).first()

    if not user_booking and not request.user.is_staff:
        messages.error(request, "Rating and reviewing is restricted to verified viewers who have booked and watched this movie.")
        return redirect('movies:detail', slug=movie.slug)

    # Check if existing review exists for this user and movie
    existing_review = Review.objects.filter(user=request.user, movie=movie).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.movie = movie
            review.booking = user_booking
            review.is_verified_viewer = True if user_booking else False
            review.status = Review.Status.APPROVED
            review.save()

            messages.success(request, 'Your review has been submitted successfully!')
            return redirect('movies:detail', slug=movie.slug)
    else:
        form = ReviewForm(instance=existing_review)

    context = {
        'movie': movie,
        'form': form,
        'existing_review': existing_review,
        'user_booking': user_booking,
    }
    return render(request, 'reviews/write_review.html', context)


@login_required
def report_review_view(request, review_id):
    review = get_object_or_404(Review, pk=review_id)

    if review.user == request.user:
        messages.error(request, "You cannot report your own review.")
        return redirect('movies:detail', slug=review.movie.slug)

    # Prevent duplicate report submission
    if ReviewReport.objects.filter(review=review, reported_by=request.user).exists():
        messages.info(request, "You have already submitted a report for this review.")
        return redirect('movies:detail', slug=review.movie.slug)

    if request.method == 'POST':
        form = ReviewReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.review = review
            report.reported_by = request.user
            report.status = ReviewReport.Status.PENDING
            report.save()

            messages.success(request, 'Thank you. The review has been reported for admin moderation.')
            return redirect('movies:detail', slug=review.movie.slug)
    else:
        form = ReviewReportForm()

    return render(request, 'reviews/report_review.html', {'review': review, 'form': form})
