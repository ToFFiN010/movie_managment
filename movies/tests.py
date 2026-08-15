from datetime import date
from django.test import TestCase
from django.urls import reverse
from movies.models import Movie, Genre, Language
from movies.utils import parse_youtube_id

class MoviesTestCase(TestCase):
    def setUp(self):
        self.lang = Language.objects.create(name='English', code='en')
        self.genre = Genre.objects.create(name='Action')
        self.movie = Movie.objects.create(
            title='Inception',
            description='Mind bending thriller.',
            release_date=date(2010, 7, 16),
            duration_minutes=148,
            language=self.lang,
            director='Christopher Nolan',
            trailer_url='https://www.youtube.com/watch?v=YoHD9XEInc0',
            status=Movie.Status.NOW_SHOWING
        )
        self.movie.genres.add(self.genre)

    def test_movie_slug_and_youtube_id(self):
        self.assertEqual(self.movie.slug, 'inception')
        self.assertEqual(self.movie.youtube_video_id, 'YoHD9XEInc0')
        parsed = parse_youtube_id('https://youtu.be/YoHD9XEInc0')
        self.assertEqual(parsed, 'YoHD9XEInc0')

    def test_movie_search_and_filter(self):
        response = self.client.get(reverse('movies:listing') + '?q=Inception')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inception')

        response = self.client.get(reverse('movies:listing') + f'?genre={self.genre.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inception')
