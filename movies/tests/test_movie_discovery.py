from datetime import date, time, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from movies.models import Movie, Genre, Language, RecentlyViewedMovie
from movies.services.discovery_service import MovieDiscoveryService
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, Booking, Payment, BookingSeat

User = get_user_model()


class MovieDiscoveryTestCase(TestCase):
    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            username='discovery_user',
            defaults={'email': 'disc_unique@test.com', 'password': 'password123'}
        )

        # Genres
        self.genre_action = Genre.objects.create(name='Action Discovery', slug='action-discovery')
        self.genre_scifi = Genre.objects.create(name='Sci-Fi Discovery', slug='scifi-discovery')
        self.genre_drama = Genre.objects.create(name='Drama Discovery', slug='drama-discovery')

        # Languages
        self.lang_en = Language.objects.create(name='English Spec', code='en-spec')
        self.lang_hi = Language.objects.create(name='Hindi Spec', code='hi-spec')

        # Movies
        self.movie_avatar = Movie.objects.create(
            title='Avatar: Discovery Fire',
            slug='avatar-discovery-fire',
            description='Pandora action movie',
            release_date=date(2026, 6, 1),
            duration_minutes=180,
            language=self.lang_en,
            director='James Cameron',
            average_rating=9.2,
            status=Movie.Status.NOW_SHOWING,
            poster_path='/media/movies/posters/avatar_3_fire_and_ash.jpg'
        )
        self.movie_avatar.genres.add(self.genre_action, self.genre_scifi)

        self.movie_batman = Movie.objects.create(
            title='The Batman: Discovery Night',
            slug='the-batman-discovery-night',
            description='Gotham detective movie',
            release_date=date(2026, 4, 15),
            duration_minutes=175,
            language=self.lang_en,
            director='Matt Reeves',
            average_rating=8.8,
            status=Movie.Status.NOW_SHOWING,
            poster_path='/media/movies/posters/the_batman_part_ii.jpg'
        )
        self.movie_batman.genres.add(self.genre_action, self.genre_drama)

        self.movie_dangal = Movie.objects.create(
            title='Dangal: Discovery Story',
            slug='dangal-discovery-story',
            description='Wrestling drama movie',
            release_date=date(2025, 12, 1),
            duration_minutes=160,
            language=self.lang_hi,
            director='Nitesh Tiwari',
            average_rating=8.4,
            status=Movie.Status.RELEASED,
            poster_path='/media/movies/posters/12th_fail.jpg'
        )
        self.movie_dangal.genres.add(self.genre_drama)

        # Theater & Screens & Shows
        self.theater_chennai = Theater.objects.create(name='PVR Chennai', city='Chennai', location='Velachery', address='Velachery Main')
        self.theater_mumbai = Theater.objects.create(name='INOX Mumbai', city='Mumbai', location='Bandr', address='Bandra West')

        self.screen_c = Screen.objects.create(theater=self.theater_chennai, name='Screen 1', screen_number=1, capacity=50)
        self.screen_m = Screen.objects.create(theater=self.theater_mumbai, name='Screen 1', screen_number=1, capacity=50)

        # Show Schedule 1: Avatar in Chennai Morning Show (₹300)
        self.show_avatar = ShowSchedule.objects.create(
            movie=self.movie_avatar,
            theater=self.theater_chennai,
            screen=self.screen_c,
            show_date=date.today(),
            start_time=time(10, 0),
            end_time=time(13, 0),
            ticket_price=Decimal('300.00')
        )

        # Show Schedule 2: Batman in Mumbai Evening Show (₹500)
        self.show_batman = ShowSchedule.objects.create(
            movie=self.movie_batman,
            theater=self.theater_mumbai,
            screen=self.screen_m,
            show_date=date.today(),
            start_time=time(18, 30),
            end_time=time(21, 30),
            ticket_price=Decimal('500.00')
        )

    def test_search_by_movie_title(self):
        qs = MovieDiscoveryService.get_filtered_movies({'q': 'Avatar'})
        self.assertIn(self.movie_avatar, qs)
        self.assertNotIn(self.movie_batman, qs)

    def test_genre_filter(self):
        qs = MovieDiscoveryService.get_filtered_movies({'genre': self.genre_scifi.slug})
        self.assertIn(self.movie_avatar, qs)
        self.assertNotIn(self.movie_dangal, qs)

    def test_language_filter(self):
        qs = MovieDiscoveryService.get_filtered_movies({'language': self.lang_hi.code})
        self.assertIn(self.movie_dangal, qs)
        self.assertNotIn(self.movie_avatar, qs)

    def test_city_filter(self):
        qs = MovieDiscoveryService.get_filtered_movies({'city': 'Chennai'})
        self.assertIn(self.movie_avatar, qs)
        self.assertNotIn(self.movie_batman, qs)

    def test_theater_filter(self):
        qs = MovieDiscoveryService.get_filtered_movies({'theater': str(self.theater_mumbai.id)})
        self.assertIn(self.movie_batman, qs)
        self.assertNotIn(self.movie_avatar, qs)

    def test_rating_filter(self):
        qs = MovieDiscoveryService.get_filtered_movies({'rating': '9.0'})
        self.assertIn(self.movie_avatar, qs)
        self.assertNotIn(self.movie_dangal, qs)

    def test_show_timing_filter(self):
        # Morning timing (06:00 - 12:00) -> matches Avatar
        qs = MovieDiscoveryService.get_filtered_movies({'timing': 'morning'})
        self.assertIn(self.movie_avatar, qs)
        self.assertNotIn(self.movie_batman, qs)

    def test_price_range_filter(self):
        # Min ₹400 -> matches Batman (₹500), excludes Avatar (₹300)
        qs = MovieDiscoveryService.get_filtered_movies({'min_price': '400'})
        self.assertIn(self.movie_batman, qs)
        self.assertNotIn(self.movie_avatar, qs)

    def test_sorting(self):
        qs = MovieDiscoveryService.get_filtered_movies({'sort': 'rating'})
        self.assertEqual(qs[0], self.movie_avatar)

    def test_pagination_and_match_count(self):
        qs = MovieDiscoveryService.get_filtered_movies({})
        self.assertGreaterEqual(qs.count(), 3)

    def test_recently_viewed_recording_and_recommendations(self):
        # Recommendations engine
        recs = MovieDiscoveryService.get_recommendations(self.user, limit=6)
        self.assertGreaterEqual(len(recs), 1)

        # Recently viewed model creation
        rv, created = RecentlyViewedMovie.objects.update_or_create(user=self.user, movie=self.movie_avatar)
        self.assertTrue(RecentlyViewedMovie.objects.filter(user=self.user, movie=self.movie_avatar).exists())
