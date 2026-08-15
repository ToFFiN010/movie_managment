from django.db.models import Count, F, Q, ExpressionWrapper, FloatField
from movies.models import Movie
from bookings.models import Booking

def get_similar_movies(movie, limit=6):
    """
    Calculates dynamic similarity score between `movie` and other movies:
    - Same genre: +3 per match
    - Same language: +2
    - Same director: +2
    - Similar rating (+/- 1.0): +1
    Returns top matching movies ordered by similarity score.
    """
    movie_genres = set(movie.genres.values_list('id', flat=True))
    other_movies = Movie.objects.exclude(id=movie.id).exclude(status=Movie.Status.ARCHIVED)

    scored_movies = []
    for other in other_movies:
        score = 0
        
        # Genre overlap (+3 per genre)
        other_genres = set(other.genres.values_list('id', flat=True))
        overlap_count = len(movie_genres.intersection(other_genres))
        score += overlap_count * 3

        # Language match (+2)
        if movie.language and other.language and movie.language == other.language:
            score += 2

        # Director match (+2)
        if movie.director and other.director and movie.director.lower() == other.director.lower():
            score += 2

        # Rating proximity (+1)
        if abs(movie.average_rating - other.average_rating) <= 1.0:
            score += 1

        if score > 0:
            scored_movies.append((score, other))

    # Sort descending by score, then by release_date
    scored_movies.sort(key=lambda item: (item[0], item[1].release_date), reverse=True)
    return [m for score, m in scored_movies[:limit]]


def get_trending_movies(limit=8):
    """
    Calculates dynamic trending score considering:
    - Total bookings count
    - Page views
    - Average rating
    - Review count
    """
    movies = Movie.objects.filter(status=Movie.Status.NOW_SHOWING).annotate(
        booking_count=Count('shows__bookings', filter=Q(shows__bookings__status=Booking.Status.CONFIRMED))
    )

    scored_movies = []
    for movie in movies:
        # Trending score formula: (bookings * 4) + (views * 0.1) + (average_rating * 3) + (reviews * 2)
        score = (movie.booking_count * 4) + (movie.views * 0.1) + (movie.average_rating * 3) + (movie.total_reviews * 2)
        scored_movies.append((score, movie))

    scored_movies.sort(key=lambda item: item[0], reverse=True)
    
    # If not enough NOW_SHOWING, fallback to all non-archived movies
    if len(scored_movies) < limit:
        remaining_needed = limit - len(scored_movies)
        existing_ids = {m.id for s, m in scored_movies}
        fallbacks = Movie.objects.exclude(id__in=existing_ids).exclude(status=Movie.Status.ARCHIVED).order_by('-average_rating', '-release_date')[:remaining_needed]
        for f in fallbacks:
            scored_movies.append((0, f))

    return [m for score, m in scored_movies[:limit]]
