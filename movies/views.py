from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, F
from django.http import JsonResponse
from .models import Movie, Genre, Language, Watchlist, MovieCast, MovieImage
from theaters.models import Theater
from bookings.models import ShowSchedule
from reviews.models import Review
from recommendations.services import get_similar_movies, get_trending_movies

def movie_listing_view(request):
    movies = Movie.objects.all()

    # Search query
    query = request.GET.get('q', '').strip()
    if query:
        movies = movies.filter(
            Q(title__icontains=query) |
            Q(director__icontains=query) |
            Q(genres__name__icontains=query) |
            Q(language__name__icontains=query) |
            Q(cast_members__cast_member__name__icontains=query)
        ).distinct()

    # Filters
    genre_id = request.GET.get('genre')
    if genre_id:
        movies = movies.filter(genres__id=genre_id)

    language_id = request.GET.get('language')
    if language_id:
        movies = movies.filter(language__id=language_id)

    age_cert = request.GET.get('age_certification')
    if age_cert:
        movies = movies.filter(age_certification=age_cert)

    status = request.GET.get('status')
    if status:
        movies = movies.filter(status=status)

    min_rating = request.GET.get('min_rating')
    if min_rating:
        try:
            movies = movies.filter(average_rating__gte=float(min_rating))
        except ValueError:
            pass

    # Featured sections
    now_showing = movies.filter(status=Movie.Status.NOW_SHOWING)[:8]
    upcoming = movies.filter(status=Movie.Status.UPCOMING)[:8]
    recently_released = movies.order_by('-release_date')[:8]
    top_rated = movies.order_by('-average_rating')[:8]
    trending = get_trending_movies(limit=8)

    genres = Genre.objects.all()
    languages = Language.objects.all()
    theaters = Theater.objects.filter(status=Theater.Status.ACTIVE)
    active_shows = ShowSchedule.objects.filter(status=ShowSchedule.Status.OPEN).select_related('movie', 'theater', 'screen')

    hero_movies = movies.filter(status=Movie.Status.NOW_SHOWING)[:5]

    context = {
        'movies': movies,
        'hero_movies': hero_movies,
        'now_showing': now_showing,
        'upcoming': upcoming,
        'recently_released': recently_released,
        'top_rated': top_rated,
        'trending': trending,
        'genres': genres,
        'languages': languages,
        'theaters': theaters,
        'active_shows': active_shows,
        'search_query': query,
        'selected_genre': genre_id,
        'selected_language': language_id,
        'selected_cert': age_cert,
        'selected_status': status,
        'total_found': movies.count() if query or genre_id or language_id or age_cert or status or min_rating else None
    }
    return render(request, 'movies/listing.html', context)


def movie_detail_view(request, slug):
    movie = get_object_or_404(Movie.objects.prefetch_related('genres', 'cast_members__cast_member', 'images'), slug=slug)

    # Increment view count safely
    Movie.objects.filter(pk=movie.pk).update(views=F('views') + 1)
    movie.refresh_from_db()

    # Show Schedules grouped by Theater
    shows = ShowSchedule.objects.filter(
        movie=movie,
        status__in=[ShowSchedule.Status.OPEN, ShowSchedule.Status.UPCOMING]
    ).select_related('theater', 'screen').order_by('show_date', 'start_time')

    # Approved Reviews
    reviews = Review.objects.filter(movie=movie, status=Review.Status.APPROVED).select_related('user').order_by('-created_at')

    # Rating distribution breakdown (5 stars down to 1 star)
    total_revs = reviews.count()
    rating_distribution = {i: 0 for i in range(5, 0, -1)}
    rating_percentages = {i: 0 for i in range(5, 0, -1)}

    if total_revs > 0:
        counts = reviews.values('rating').annotate(count=Count('id'))
        for c in counts:
            rating_distribution[c['rating']] = c['count']
            rating_percentages[c['rating']] = int(round((c['count'] / total_revs) * 100))

    # Similar movies recommendation
    similar_movies = get_similar_movies(movie, limit=6)

    # Check if in user watchlist
    in_watchlist = False
    if request.user.is_authenticated:
        in_watchlist = Watchlist.objects.filter(user=request.user, movie=movie).exists()

    context = {
        'movie': movie,
        'shows': shows,
        'reviews': reviews,
        'rating_distribution': rating_distribution,
        'rating_percentages': rating_percentages,
        'similar_movies': similar_movies,
        'in_watchlist': in_watchlist,
    }
    return render(request, 'movies/detail.html', context)


@login_required
def watchlist_toggle_view(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    watchlist_item = Watchlist.objects.filter(user=request.user, movie=movie).first()

    if watchlist_item:
        watchlist_item.delete()
        added = False
        msg = f"'{movie.title}' removed from Watchlist."
    else:
        Watchlist.objects.create(user=request.user, movie=movie)
        added = True
        msg = f"'{movie.title}' added to Watchlist."

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'added': added, 'message': msg})

    messages.success(request, msg)
    return redirect('movies:detail', slug=movie.slug)


@login_required
def watchlist_view(request):
    watchlist_items = Watchlist.objects.filter(user=request.user).select_related('movie')
    context = {
        'watchlist_items': watchlist_items,
    }
    return render(request, 'movies/watchlist.html', context)


def theaters_view(request):
    theaters = Theater.objects.filter(status=Theater.Status.ACTIVE).prefetch_related('screens')

    city_filter = request.GET.get('city', '').strip()
    query = request.GET.get('q', '').strip()

    if city_filter:
        theaters = theaters.filter(city__iexact=city_filter)
    if query:
        theaters = theaters.filter(
            Q(name__icontains=query) |
            Q(city__icontains=query) |
            Q(location__icontains=query) |
            Q(facilities__icontains=query)
        )

    cities = Theater.objects.values_list('city', flat=True).distinct()
    active_shows = ShowSchedule.objects.filter(status=ShowSchedule.Status.OPEN).select_related('movie', 'theater', 'screen')

    context = {
        'theaters': theaters,
        'cities': cities,
        'selected_city': city_filter,
        'search_query': query,
        'active_shows': active_shows,
    }
    return render(request, 'movies/theaters.html', context)


def search_view(request):
    query = request.GET.get('q', '').strip()
    if not query:
        trending_movies = Movie.objects.filter(status=Movie.Status.NOW_SHOWING).order_by('-average_rating')[:6]
        return render(request, 'movies/search.html', {
            'best_matches': [],
            'related_movies': [],
            'trending_movies': trending_movies,
            'search_query': '',
            'total_found': 0,
        })

    # Step 1: Filter movies matching the query across all metadata fields
    matching_qs = Movie.objects.filter(
        Q(title__icontains=query) |
        Q(director__icontains=query) |
        Q(description__icontains=query) |
        Q(genres__name__icontains=query) |
        Q(language__name__icontains=query) |
        Q(cast_members__cast_member__name__icontains=query)
    ).distinct().prefetch_related('genres', 'language', 'cast_members')

    # Step 2: Score matching movies (exact title > title starts with > title contains > director/genre/cast)
    scored_matches = []
    q_lower = query.lower()
    for movie in matching_qs:
        title_lower = movie.title.lower()
        score = 0
        if title_lower == q_lower:
            score += 100
        elif title_lower.startswith(q_lower):
            score += 50
        elif q_lower in title_lower:
            score += 30

        if movie.director and q_lower in movie.director.lower():
            score += 15

        for g in movie.genres.all():
            if q_lower in g.name.lower():
                score += 10

        if movie.description and q_lower in movie.description.lower():
            score += 5

        score += (movie.average_rating or 0.0)
        scored_matches.append((score, movie))

    scored_matches.sort(key=lambda x: x[0], reverse=True)
    best_matches = [m[1] for m in scored_matches]

    # Step 3: Calculate Related Movies based on matching movie metadata (Genre, Language, Director)
    related_movies = []
    matched_ids = [m.id for m in best_matches]

    if best_matches:
        genre_ids = set()
        lang_ids = set()
        directors = set()
        for m in best_matches:
            genre_ids.update(m.genres.values_list('id', flat=True))
            if m.language_id:
                lang_ids.add(m.language_id)
            if m.director:
                directors.add(m.director)

        related_qs = Movie.objects.exclude(id__in=matched_ids).filter(
            Q(genres__id__in=genre_ids) |
            Q(language__id__in=lang_ids) |
            Q(director__in=directors)
        ).distinct().prefetch_related('genres', 'language')

        scored_related = []
        for r_movie in related_qs:
            r_score = 0
            r_genre_ids = set(r_movie.genres.values_list('id', flat=True))
            common_genres = len(genre_ids.intersection(r_genre_ids))
            r_score += common_genres * 3

            if r_movie.language_id in lang_ids:
                r_score += 2
            if r_movie.director in directors:
                r_score += 3

            r_score += (r_movie.average_rating or 0.0)
            scored_related.append((r_score, r_movie))

        scored_related.sort(key=lambda x: x[0], reverse=True)
        related_movies = [m[1] for m in scored_related[:6]]

    # Step 4: Trending / Recommended Movies Fallback
    excluded_ids = matched_ids + [m.id for m in related_movies]
    trending_movies = Movie.objects.exclude(id__in=excluded_ids).order_by('-average_rating', '-release_date')[:6]

    context = {
        'best_matches': best_matches,
        'related_movies': related_movies,
        'trending_movies': trending_movies,
        'search_query': query,
        'total_found': len(best_matches),
    }
    return render(request, 'movies/search.html', context)


def movie_api_detail(request, movie_id):
    """
    JSON API endpoint returning full movie metadata for cinematic detail popups.
    """
    movie = get_object_or_404(Movie.objects.prefetch_related('genres', 'cast_members__cast_member'), pk=movie_id)
    
    in_watchlist = False
    if request.user.is_authenticated:
        in_watchlist = Watchlist.objects.filter(user=request.user, movie=movie).exists()

    cast_list = []
    for cm in movie.cast_members.all()[:6]:
        cast_list.append({
            'name': cm.cast_member.name,
            'character': cm.character_name or cm.role,
            'role': cm.role,
        })

    genres_list = [g.name for g in movie.genres.all()]

    data = {
        'id': movie.id,
        'title': movie.title,
        'slug': movie.slug,
        'description': movie.description or movie.short_description,
        'release_year': movie.release_date.strftime('%Y') if movie.release_date else '',
        'duration_minutes': movie.duration_minutes,
        'age_certification': movie.age_certification,
        'language': movie.language.name if movie.language else 'English',
        'director': movie.director or 'N/A',
        'average_rating': f"{movie.average_rating:.1f}",
        'poster_url': movie.get_poster_url,
        'backdrop_url': movie.get_backdrop_url,
        'trailer_url': movie.trailer_url or '',
        'youtube_video_id': movie.youtube_video_id or movie.extract_youtube_id() or '',
        'genres': genres_list,
        'cast': cast_list,
        'in_watchlist': in_watchlist,
        'booking_url': f"/bookings/movie/{movie.id}/",
    }
    return JsonResponse(data)


def search_suggestions_api(request):
    """
    JSON API endpoint for live navbar search dropdown suggestions.
    """
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    matches = Movie.objects.filter(
        Q(title__icontains=query) |
        Q(director__icontains=query) |
        Q(genres__name__icontains=query)
    ).distinct().prefetch_related('genres', 'language')[:6]

    results = []
    for m in matches:
        results.append({
            'id': m.id,
            'title': m.title,
            'slug': m.slug,
            'poster_url': m.get_poster_url,
            'average_rating': f"{m.average_rating:.1f}",
            'release_year': m.release_date.strftime('%Y') if m.release_date else '',
            'language': m.language.name if m.language else '',
            'detail_url': f"/{m.slug}/",
        })

    return JsonResponse({'results': results})



