import os
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

    # Showtimes Summary Stats
    todays_shows_count = ShowSchedule.objects.filter(show_date=today).count()
    upcoming_shows_count = ShowSchedule.objects.filter(show_date__gt=today).count()
    cancelled_shows_count = ShowSchedule.objects.filter(status=ShowSchedule.Status.CANCELLED).count()
    completed_shows_count = ShowSchedule.objects.filter(status=ShowSchedule.Status.CLOSED).count()

    recent_showtimes = ShowSchedule.objects.select_related('movie', 'theater', 'screen').annotate(
        confirmed_bookings=Count('bookings', filter=Q(bookings__status=Booking.Status.CONFIRMED)),
        revenue=Sum('bookings__total_amount', filter=Q(bookings__status=Booking.Status.CONFIRMED))
    ).order_by('-show_date', '-start_time')[:10]

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
        
        # Showtimes Dashboard Summary
        'todays_shows_count': todays_shows_count,
        'upcoming_shows_count': upcoming_shows_count,
        'cancelled_shows_count': cancelled_shows_count,
        'completed_shows_count': completed_shows_count,
        'recent_showtimes': recent_showtimes,
    }
    return render(request, 'admin_custom/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_movie_images_audit_view(request):
    import os
    import hashlib
    from collections import defaultdict
    from PIL import Image
    from django.conf import settings
    
    status_filter = request.GET.get('status', 'all').lower()

    movies = Movie.objects.all().order_by('id')
    total_movies = movies.count()
    
    valid_cnt = 0
    missing_cnt = 0
    broken_cnt = 0
    placeholder_cnt = 0
    hash_map = defaultdict(list)

    audited_movies = []

    for movie in movies:
        item = {
            'id': movie.id,
            'title': movie.title,
            'release_date': movie.release_date,
            'director': movie.director,
            'poster_url': movie.get_poster_url,
            'poster_name': movie.poster.name if movie.poster else 'NONE',
            'status_code': 'VALID',
            'status_label': 'Valid',
            'dimensions': '-',
            'size_kb': '0',
            'format': '-',
        }

        if not movie.poster or not movie.poster.name:
            item['status_code'] = 'MISSING'
            item['status_label'] = 'Missing'
            missing_cnt += 1
        else:
            abs_p = settings.MEDIA_ROOT / movie.poster.name
            if not abs_p.exists():
                item['status_code'] = 'BROKEN'
                item['status_label'] = 'File Not Found'
                broken_cnt += 1
            elif abs_p.stat().st_size == 0:
                item['status_code'] = 'BROKEN'
                item['status_label'] = 'Zero Byte File'
                broken_cnt += 1
            else:
                kb = round(abs_p.stat().st_size / 1024, 1)
                item['size_kb'] = str(kb)
                try:
                    with open(abs_p, 'rb') as f:
                        h = hashlib.md5(f.read()).hexdigest()
                    hash_map[h].append(movie.id)

                    with Image.open(abs_p) as im:
                        item['format'] = im.format or 'UNKNOWN'
                        w, h = im.size
                        item['dimensions'] = f"{w}x{h}"

                    if 'placeholder' in movie.poster.name.lower():
                        item['status_code'] = 'PLACEHOLDER'
                        item['status_label'] = 'Placeholder'
                        placeholder_cnt += 1
                    else:
                        valid_cnt += 1
                except Exception:
                    item['status_code'] = 'BROKEN'
                    item['status_label'] = 'Corrupt Image'
                    broken_cnt += 1

        audited_movies.append(item)

    # Detect duplicates
    duplicate_movie_ids = set()
    for h, m_ids in hash_map.items():
        if len(m_ids) > 1:
            duplicate_movie_ids.update(m_ids)
            for item in audited_movies:
                if item['id'] in m_ids:
                    item['is_duplicate'] = True

    duplicate_cnt = len(duplicate_movie_ids)

    # Apply filtering
    if status_filter == 'valid':
        filtered_list = [m for m in audited_movies if m['status_code'] == 'VALID']
    elif status_filter == 'missing':
        filtered_list = [m for m in audited_movies if m['status_code'] == 'MISSING']
    elif status_filter == 'broken':
        filtered_list = [m for m in audited_movies if m['status_code'] == 'BROKEN']
    elif status_filter == 'placeholder':
        filtered_list = [m for m in audited_movies if m['status_code'] == 'PLACEHOLDER']
    elif status_filter == 'duplicate':
        filtered_list = [m for m in audited_movies if m.get('is_duplicate')]
    else:
        filtered_list = audited_movies

    context = {
        'total_movies': total_movies,
        'valid_cnt': valid_cnt,
        'missing_cnt': missing_cnt,
        'broken_cnt': broken_cnt,
        'placeholder_cnt': placeholder_cnt,
        'duplicate_cnt': duplicate_cnt,
        'audited_movies': filtered_list,
        'selected_status': status_filter,
    }
    return render(request, 'admin_custom/movie_images_audit.html', context)


@login_required
@user_passes_test(is_admin)
def admin_movie_media_health_view(request):
    import csv
    from django.http import HttpResponse
    from django.contrib import messages
    from movies.utils import get_youtube_video_id
    from movies.management.commands.repair_movie_media import Command as RepairMediaCmd
    from movies.management.commands.validate_movie_media import Command as ValidateMediaCmd
    from movies.management.commands.validate_movie_trailers import Command as ValidateTrailerCmd
    from movies.management.commands.repair_movie_trailers import Command as RepairTrailerCmd

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'repair_posters':
            RepairMediaCmd().handle(force=True)
            messages.success(request, "✓ Executed Repair Missing Posters pipeline!")
        elif action == 'validate_posters':
            ValidateMediaCmd().handle()
            messages.info(request, "✓ Completed Poster Validation inspection.")
        elif action == 'validate_trailers':
            ValidateTrailerCmd().handle()
            messages.info(request, "✓ Completed Trailer Validation inspection.")
        elif action == 'repair_trailers':
            RepairTrailerCmd().handle(force=True)
            messages.success(request, "✓ Executed Repair Trailers pipeline!")
        elif action == 'export_report':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="CinePrime_Movie_Media_Health_Report.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Title', 'Release Year', 'Poster Status', 'Trailer Status', 'Media Status', 'TMDb ID', 'YouTube Video ID'])

            for m in Movie.objects.all().order_by('id'):
                p_status = 'OK' if m.poster and os.path.exists(m.poster.path) else 'MISSING'
                v_id = get_youtube_video_id(m.trailer_url or m.youtube_video_id)
                t_status = 'OK' if v_id and len(v_id) == 11 else 'MISSING'
                writer.writerow([m.id, m.title, m.release_year, p_status, t_status, m.media_status, m.tmdb_id or '', v_id or ''])
            return response

        return redirect('admin_movie_media_health')

    movies = Movie.objects.all()
    total_movies = movies.count()

    posters_complete = 0
    posters_missing = 0
    broken_posters = 0

    trailers_complete = 0
    trailers_missing = 0
    trailers_invalid = 0

    manual_review_cnt = 0

    for m in movies:
        if m.media_status == 'manual_review':
            manual_review_cnt += 1

        if m.poster:
            try:
                if os.path.exists(m.poster.path) and os.path.getsize(m.poster.path) > 0:
                    posters_complete += 1
                else:
                    broken_posters += 1
            except Exception:
                broken_posters += 1
        else:
            posters_missing += 1

        v_id = get_youtube_video_id(m.trailer_url or m.youtube_video_id)
        if v_id and len(v_id) == 11:
            trailers_complete += 1
        elif m.trailer_url or m.youtube_video_id:
            trailers_invalid += 1
        else:
            trailers_missing += 1

    context = {
        'total_movies': total_movies,
        'posters_complete': posters_complete,
        'posters_missing': posters_missing,
        'broken_posters': broken_posters,
        'trailers_complete': trailers_complete,
        'trailers_missing': trailers_missing,
        'trailers_invalid': trailers_invalid,
        'manual_review_cnt': manual_review_cnt,
    }
    return render(request, 'admin_custom/movie_media_health.html', context)


# Alias for backward compatibility
admin_movie_image_status_view = admin_movie_media_health_view


@login_required
@user_passes_test(is_admin)
def admin_movie_trailers_audit_view(request):
    from django.contrib import messages
    from movies.models import MovieTrailer
    from movies.services.youtube_trailer import extract_youtube_id, classify_trailer_type

    if request.method == 'POST':
        movie_id = request.POST.get('movie_id')
        raw_url = request.POST.get('youtube_url', '').strip()

        if movie_id and raw_url:
            vid = extract_youtube_id(raw_url)
            if vid:
                try:
                    movie = Movie.objects.get(pk=movie_id)
                    yt_url = f"https://www.youtube.com/watch?v={vid}"
                    v_title = f"{movie.title} — Official Trailer"
                    
                    tr, created = MovieTrailer.objects.update_or_create(
                        movie=movie,
                        video_id=vid,
                        defaults={
                            'trailer_url': yt_url,
                            'video_title': v_title,
                            'channel_name': 'Manual Admin Assignment',
                            'trailer_type': classify_trailer_type(v_title),
                            'is_primary': True,
                            'confidence_score': 100,
                            'verification_status': MovieTrailer.VerificationStatus.VERIFIED,
                            'verification_date': timezone.now(),
                            'thumbnail_url': f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                            'notes_or_reason': 'Manually assigned by admin',
                        }
                    )
                    messages.success(request, f"✓ Assigned Official Trailer (ID: {vid}) for '{movie.title}'!")
                except Movie.DoesNotExist:
                    messages.error(request, "Movie not found.")
            else:
                messages.error(request, "Invalid YouTube URL or Video ID format.")

        return redirect('admin_movie_trailers_audit')

    status_filter = request.GET.get('status', 'all').lower()

    movies = Movie.objects.all().order_by('id')
    total_movies = movies.count()

    verified_cnt = MovieTrailer.objects.filter(is_primary=True, verification_status='VERIFIED').count()
    manual_review_cnt = MovieTrailer.objects.filter(verification_status='MANUAL_REVIEW_REQUIRED').count()
    no_trailer_cnt = movies.filter(Q(trailers__isnull=True) | Q(trailers__verification_status='NO_TRAILER_FOUND')).distinct().count()
    broken_cnt = MovieTrailer.objects.filter(verification_status__in=['TRAILER_BROKEN', 'TRAILER_UNAVAILABLE']).count()

    audited_trailers = []

    for movie in movies:
        primary_tr = movie.primary_trailer
        item = {
            'movie_id': movie.id,
            'title': movie.title,
            'release_year': movie.release_year,
            'director': movie.director,
            'has_trailer': bool(primary_tr),
            'video_id': primary_tr.video_id if primary_tr else (movie.youtube_video_id or 'NONE'),
            'trailer_title': primary_tr.video_title if primary_tr else (movie.trailer_title or 'No Official Trailer Assigned'),
            'channel_name': primary_tr.channel_name if primary_tr else 'N/A',
            'trailer_type': primary_tr.get_trailer_type_display() if primary_tr else 'OFFICIAL_TRAILER',
            'confidence_score': primary_tr.confidence_score if primary_tr else 0,
            'verification_status': primary_tr.verification_status if primary_tr else ('VERIFIED' if movie.youtube_video_id else 'NO_TRAILER_FOUND'),
            'is_primary': primary_tr.is_primary if primary_tr else False,
            'trailer_url': primary_tr.trailer_url if primary_tr else (movie.trailer_url or ''),
            'thumbnail_url': primary_tr.thumbnail_url if primary_tr else (movie.trailer_thumbnail_url or (f"https://img.youtube.com/vi/{movie.youtube_video_id}/hqdefault.jpg" if movie.youtube_video_id else '')),
        }
        audited_trailers.append(item)

    # Filter logic
    if status_filter == 'verified':
        filtered = [t for t in audited_trailers if t['verification_status'] == 'VERIFIED']
    elif status_filter == 'manual_review':
        filtered = [t for t in audited_trailers if t['verification_status'] == 'MANUAL_REVIEW_REQUIRED']
    elif status_filter == 'missing':
        filtered = [t for t in audited_trailers if not t['has_trailer'] or t['verification_status'] == 'NO_TRAILER_FOUND']
    elif status_filter == 'broken':
        filtered = [t for t in audited_trailers if t['verification_status'] in ['TRAILER_BROKEN', 'TRAILER_UNAVAILABLE']]
    else:
        filtered = audited_trailers

    context = {
        'total_movies': total_movies,
        'verified_cnt': verified_cnt,
        'manual_review_cnt': manual_review_cnt,
        'no_trailer_cnt': no_trailer_cnt,
        'broken_cnt': broken_cnt,
        'audited_trailers': filtered,
        'selected_status': status_filter,
    }
    return render(request, 'admin_custom/movie_trailers_audit.html', context)


