from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from movies.models import Movie, MovieTrailer, Language, Genre
from movies.services.youtube_trailer import (
    extract_youtube_id,
    score_trailer_candidate,
    classify_trailer_type
)

class MovieTrailerSystemTests(TestCase):
    def setUp(self):
        self.language = Language.objects.create(name='English', code='en')
        self.genre = Genre.objects.create(name='Action')
        self.movie = Movie.objects.create(
            title='Oppenheimer',
            description='Biographical drama movie',
            release_date=date(2023, 7, 21),
            duration_minutes=180,
            director='Christopher Nolan',
            language=self.language,
        )
        self.movie.genres.add(self.genre)

        self.admin_user = User.objects.create_superuser(
            username='admin_trailer',
            email='admin_trailer@cineprime.com',
            password='Password123!',
            role=User.Role.ADMIN
        )

    def test_extract_youtube_id(self):
        self.assertEqual(extract_youtube_id('https://www.youtube.com/watch?v=uYPbbksJxIg'), 'uYPbbksJxIg')
        self.assertEqual(extract_youtube_id('https://youtu.be/uYPbbksJxIg'), 'uYPbbksJxIg')
        self.assertEqual(extract_youtube_id('https://www.youtube.com/embed/uYPbbksJxIg'), 'uYPbbksJxIg')
        self.assertEqual(extract_youtube_id('uYPbbksJxIg'), 'uYPbbksJxIg')
        self.assertIsNone(extract_youtube_id('javascript:alert(1)'))
        self.assertIsNone(extract_youtube_id('https://malicious.com/video'))

    def test_single_primary_trailer_constraint(self):
        tr1 = MovieTrailer.objects.create(
            movie=self.movie,
            trailer_url='https://www.youtube.com/watch?v=uYPbbksJxIg',
            video_id='uYPbbksJxIg',
            video_title='Oppenheimer Official Teaser',
            channel_name='Warner Bros. Pictures',
            is_primary=True,
            verification_status=MovieTrailer.VerificationStatus.VERIFIED
        )
        self.assertTrue(tr1.is_primary)
        self.assertEqual(self.movie.youtube_video_id, 'uYPbbksJxIg')

        # Create second primary trailer
        tr2 = MovieTrailer.objects.create(
            movie=self.movie,
            trailer_url='https://www.youtube.com/watch?v=Way9Dexny3w',
            video_id='Way9Dexny3w',
            video_title='Oppenheimer Official Main Trailer',
            channel_name='Universal Pictures',
            is_primary=True,
            verification_status=MovieTrailer.VerificationStatus.VERIFIED
        )

        tr1.refresh_from_db()
        tr2.refresh_from_db()
        self.movie.refresh_from_db()

        self.assertFalse(tr1.is_primary)
        self.assertTrue(tr2.is_primary)
        self.assertEqual(self.movie.youtube_video_id, 'Way9Dexny3w')
        self.assertEqual(self.movie.primary_trailer, tr2)

    def test_scoring_engine_auto_approve(self):
        candidate = {
            'video_id': 'uYPbbksJxIg',
            'video_title': 'Oppenheimer — Official Trailer (2023)',
            'channel_name': 'Universal Pictures',
            'description': 'Official trailer for Oppenheimer directed by Christopher Nolan.',
            'published_at': '2023-05-08T00:00:00Z',
        }
        score, decision, reason, t_type = score_trailer_candidate(candidate, self.movie)
        self.assertGreaterEqual(score, 90)
        self.assertEqual(decision, 'AUTO_APPROVE')
        self.assertEqual(t_type, 'OFFICIAL_TRAILER')

    def test_scoring_engine_blacklisted_rejection(self):
        candidate = {
            'video_id': 'abc12345678',
            'video_title': 'Oppenheimer Fan Made Reaction Review Edit (2023)',
            'channel_name': 'Fan Movie Clips Channel',
            'description': 'Reaction and breakdown video',
            'published_at': '2023-05-08T00:00:00Z',
        }
        score, decision, reason, t_type = score_trailer_candidate(candidate, self.movie)
        self.assertEqual(score, 0)
        self.assertEqual(decision, 'REJECT')
        self.assertIn("Blacklisted keyword found", reason)

    def test_admin_trailer_audit_view_access(self):
        client = Client()
        url = reverse('admin_movie_trailers_audit')
        
        # Unauthenticated redirect
        res = client.get(url)
        self.assertEqual(res.status_code, 302)

        # Authenticated Admin access
        client.force_login(self.admin_user)
        res_admin = client.get(url)
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, 'Oppenheimer')
