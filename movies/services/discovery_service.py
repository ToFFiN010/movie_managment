from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models import Q, Count, Min, Max, F, ExpressionWrapper, FloatField
from django.utils import timezone

from movies.models import Movie, Genre, Language, RecentlyViewedMovie
from theaters.models import Theater
from bookings.models import ShowSchedule, Booking, BookingSeat


import re
import difflib

class MovieDiscoveryService:
    @staticmethod
    def build_smart_search_q(q_string):
        """
        Builds a robust, tokenized, punctuation-insensitive, typo-tolerant Django Q search filter.
        Handles hyphenated names (Spider-Man / Spider man), typos (sallar -> Salaar), numbers (kgf 2), etc.
        """
        q_str = q_string.strip()
        if not q_str:
            return Q()

        # Direct exact or substring matches across all text fields
        q_filter = (
            Q(title__icontains=q_str) |
            Q(director__icontains=q_str) |
            Q(cast_members__cast_member__name__icontains=q_str) |
            Q(description__icontains=q_str) |
            Q(genres__name__icontains=q_str) |
            Q(language__name__icontains=q_str)
        )

        # Space / hyphen variation (e.g., 'spider man' <-> 'spider-man')
        alt_space = q_str.replace('-', ' ')
        alt_hyphen = q_str.replace(' ', '-')
        if alt_space != q_str:
            q_filter |= Q(title__icontains=alt_space) | Q(director__icontains=alt_space)
        if alt_hyphen != q_str:
            q_filter |= Q(title__icontains=alt_hyphen) | Q(director__icontains=alt_hyphen)

        # Tokenized search (e.g. 'KGF Chapter 2' -> tokens: 'KGF', 'Chapter', '2')
        cleaned = re.sub(r'[^\w\s]', ' ', q_str)
        tokens = [t.strip() for t in cleaned.split() if len(t.strip()) >= 2]
        if tokens:
            for token in tokens:
                q_filter |= (
                    Q(title__icontains=token) |
                    Q(director__icontains=token) |
                    Q(cast_members__cast_member__name__icontains=token) |
                    Q(genres__name__icontains=token)
                )

        # Fuzzy string similarity matching against all movie titles & directors
        try:
            all_movies = list(Movie.objects.values_list('id', 'title', 'director'))
            for m_id, m_title, m_director in all_movies:
                # Compare full title
                if difflib.SequenceMatcher(None, q_str.lower(), m_title.lower()).ratio() > 0.55:
                    q_filter |= Q(id=m_id)
                else:
                    # Compare individual title words
                    for word in m_title.lower().replace('-', ' ').split():
                        if len(word) >= 3 and difflib.SequenceMatcher(None, q_str.lower(), word).ratio() > 0.7:
                            q_filter |= Q(id=m_id)
                            break

                if m_director and difflib.SequenceMatcher(None, q_str.lower(), m_director.lower()).ratio() > 0.6:
                    q_filter |= Q(id=m_id)
        except Exception:
            pass

        return q_filter

    @staticmethod
    def get_filtered_movies(params):
        """
        Executes database-level search, filtering, and sorting for movies.
        Returns a distinct, optimized Movie QuerySet with annotated min_ticket_price and booking_count.
        """
        queryset = Movie.objects.select_related('language').prefetch_related('genres').annotate(
            min_ticket_price=Min('shows__ticket_price'),
            booking_count=Count('shows__bookings', filter=Q(shows__bookings__status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]))
        )

        # 1. Search Query (Title, Director, Cast, Description, Genre, Language)
        q = params.get('q', '').strip()
        if q:
            search_q = MovieDiscoveryService.build_smart_search_q(q)
            queryset = queryset.filter(search_q)

        # 2. Genre Filter
        genre_param = params.get('genre', '').strip()
        if genre_param and genre_param != 'all':
            if genre_param.isdigit():
                queryset = queryset.filter(genres__id=int(genre_param))
            else:
                queryset = queryset.filter(genres__slug__iexact=genre_param)

        # 3. Language Filter
        lang_param = params.get('language', '').strip()
        if lang_param and lang_param != 'all':
            if lang_param.isdigit():
                queryset = queryset.filter(language__id=int(lang_param))
            else:
                queryset = queryset.filter(
                    Q(language__code__iexact=lang_param) | Q(language__name__iexact=lang_param)
                )

        # 4. City Filter (Movies with active/upcoming shows in selected city)
        city_param = params.get('city', '').strip()
        if city_param and city_param != 'all':
            queryset = queryset.filter(shows__theater__city__iexact=city_param)

        # 5. Theater Filter (Movies with shows at selected theater)
        theater_param = params.get('theater', '').strip()
        if theater_param and theater_param != 'all':
            if theater_param.isdigit():
                queryset = queryset.filter(shows__theater__id=int(theater_param))
            else:
                queryset = queryset.filter(shows__theater__name__icontains=theater_param)

        # 6. Release Date Filter
        release_date_opt = params.get('release_date', '').strip()
        today = date.today()

        if release_date_opt == 'today':
            queryset = queryset.filter(release_date=today)
        elif release_date_opt == 'this_week':
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            queryset = queryset.filter(release_date__range=[start_week, end_week])
        elif release_date_opt == 'this_month':
            queryset = queryset.filter(release_date__year=today.year, release_date__month=today.month)
        elif release_date_opt == 'this_year':
            queryset = queryset.filter(release_date__year=today.year)
        elif release_date_opt == 'upcoming':
            queryset = queryset.filter(Q(release_date__gt=today) | Q(status=Movie.Status.UPCOMING))

        # Custom Release Date Range
        release_from = params.get('release_from', '').strip()
        release_to = params.get('release_to', '').strip()
        if release_from:
            try:
                d_from = datetime.strptime(release_from, '%Y-%m-%d').date()
                queryset = queryset.filter(release_date__gte=d_from)
            except ValueError:
                pass
        if release_to:
            try:
                d_to = datetime.strptime(release_to, '%Y-%m-%d').date()
                queryset = queryset.filter(release_date__lte=d_to)
            except ValueError:
                pass

        # 7. Minimum Rating Filter
        rating_param = params.get('rating', '').strip()
        if rating_param and rating_param != 'all':
            try:
                min_r = float(rating_param)
                queryset = queryset.filter(average_rating__gte=min_r)
            except ValueError:
                pass

        # 8. Show Timing Filter
        timing_param = params.get('timing', '').strip().lower()
        if timing_param and timing_param != 'all':
            if timing_param == 'morning':
                queryset = queryset.filter(shows__start_time__range=['06:00:00', '11:59:59'])
            elif timing_param == 'afternoon':
                queryset = queryset.filter(shows__start_time__range=['12:00:00', '16:59:59'])
            elif timing_param == 'evening':
                queryset = queryset.filter(shows__start_time__range=['17:00:00', '20:59:59'])
            elif timing_param == 'night':
                queryset = queryset.filter(
                    Q(shows__start_time__range=['21:00:00', '23:59:59']) | Q(shows__start_time__range=['00:00:00', '02:00:00'])
                )

        # 9. Ticket Price Filter
        min_price = params.get('min_price', '').strip()
        max_price = params.get('max_price', '').strip()
        if min_price:
            try:
                p_min = Decimal(min_price)
                queryset = queryset.filter(shows__ticket_price__gte=p_min)
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                p_max = Decimal(max_price)
                queryset = queryset.filter(shows__ticket_price__lte=p_max)
            except (ValueError, TypeError):
                pass

        # 10. Movie Status Filter (NOW_SHOWING, UPCOMING, RELEASED, ENDED)
        status_param = params.get('status', '').strip()
        if status_param and status_param != 'all':
            queryset = queryset.filter(status__iexact=status_param)

        # 11. Distinct before sorting to avoid duplicate rows from joins
        queryset = queryset.distinct()

        # 12. Sorting
        sort_param = params.get('sort', 'newest').strip().lower()
        if sort_param == 'oldest':
            queryset = queryset.order_by('release_date', 'title')
        elif sort_param == 'popular':
            queryset = queryset.order_by('-booking_count', '-average_rating', '-release_date')
        elif sort_param in ['rating', 'highest_rated']:
            queryset = queryset.order_by('-average_rating', '-release_date')
        elif sort_param in ['title_asc', 'a_z', 'az']:
            queryset = queryset.order_by('title')
        elif sort_param in ['title_desc', 'z_a', 'za']:
            queryset = queryset.order_by('-title')
        elif sort_param in ['price_low', 'lowest_price']:
            queryset = queryset.order_by('min_ticket_price', '-average_rating')
        elif sort_param in ['price_high', 'highest_price']:
            queryset = queryset.order_by('-min_ticket_price', '-average_rating')
        else: # Default: newest
            queryset = queryset.order_by('-release_date', 'title')

        return queryset

    @staticmethod
    def get_recommendations(user=None, limit=6):
        """
        Generates personalized movie recommendations.
        For authenticated users: Based on booking history genres/languages + recently viewed movies.
        For guest users: Returns trending/top-rated movies.
        """
        if not user or not getattr(user, 'is_authenticated', False):
            popular_movies = list(Movie.objects.select_related('language').prefetch_related('genres').order_by('-average_rating', '-views')[:limit])
            for m in popular_movies:
                m.recommendation_reason = "Popular on CinePrime"
            return popular_movies

        # 1. User's booked genres & languages
        user_bookings = Booking.objects.filter(
            user=user,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]
        ).select_related('show__movie')

        booked_movie_ids = set(user_bookings.values_list('show__movie_id', flat=True))
        
        user_genres = set()
        user_languages = set()

        for b in user_bookings:
            if b.show and b.show.movie:
                user_languages.add(b.show.movie.language_id)
                user_genres.update(b.show.movie.genres.values_list('id', flat=True))

        # 2. User's recently viewed movies
        recently_viewed = RecentlyViewedMovie.objects.filter(user=user).select_related('movie').order_by('-viewed_at')[:10]
        recent_movie_ids = set(rv.movie_id for rv in recently_viewed)
        for rv in recently_viewed:
            if rv.movie and rv.movie.language_id:
                user_languages.add(rv.movie.language_id)
            if rv.movie:
                user_genres.update(rv.movie.genres.values_list('id', flat=True))

        # 3. Fetch candidate movies excluding already booked movies
        candidates = Movie.objects.select_related('language').prefetch_related('genres').exclude(id__in=booked_movie_ids)

        if not candidates.exists():
            candidates = Movie.objects.select_related('language').prefetch_related('genres').all()

        recommended = []
        for movie in candidates[:30]:
            score = 0
            reason = "Popular on CinePrime"

            # Check genre overlap
            movie_genre_ids = set(movie.genres.values_list('id', flat=True))
            matching_genres = movie_genre_ids.intersection(user_genres)
            if matching_genres:
                matched_genre_name = Genre.objects.filter(id=list(matching_genres)[0]).values_list('name', flat=True).first()
                score += 5
                reason = f"Because you watched {matched_genre_name or 'similar'} movies"

            # Check language match
            if movie.language_id in user_languages:
                score += 4
                if score <= 4:
                    reason = f"Top release in {movie.language.name if movie.language else 'your language'}"

            # Check recently viewed similarity
            if movie.id in recent_movie_ids:
                score += 2
                reason = "Recently Viewed"

            score += (movie.average_rating or 0)
            movie.recommendation_score = score
            movie.recommendation_reason = reason
            recommended.append(movie)

        # Sort candidate movies by recommendation_score descending
        recommended.sort(key=lambda m: getattr(m, 'recommendation_score', 0), reverse=True)
        return recommended[:limit]
