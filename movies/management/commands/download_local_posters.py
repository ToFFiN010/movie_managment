import os
import urllib.request
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie

POSTER_DOWNLOADS = {
    "Jawan": "https://upload.wikimedia.org/wikipedia/en/3/39/Jawan_film_poster.jpg",
    "Salaar": "https://upload.wikimedia.org/wikipedia/en/a/a6/Salaar_Part_1_%E2%80%93_Ceasefire.jpg",
    "Kalki 2898 AD": "https://upload.wikimedia.org/wikipedia/en/4/4c/Kalki_2898_AD.jpg",
    "KGF: Chapter 2": "https://upload.wikimedia.org/wikipedia/en/d/d0/K.G.F_Chapter_2.jpg",
    "12th Fail": "https://upload.wikimedia.org/wikipedia/en/f/f2/12th_Fail_poster.jpeg",
    "Kantara: Chapter 1": "https://upload.wikimedia.org/wikipedia/en/8/84/Kantara_poster.jpeg"
}

class Command(BaseCommand):
    help = 'Downloads high-quality local movie posters for seamless rendering without CDN rate limiting.'

    def handle(self, *args, **options):
        posters_dir = os.path.join(settings.MEDIA_ROOT, 'movies', 'posters')
        os.makedirs(posters_dir, exist_ok=True)

        for title, url in POSTER_DOWNLOADS.items():
            ext = '.jpeg' if url.endswith('.jpeg') else '.jpg'
            filename = f"{title.lower().replace(' ', '_').replace(':', '')}{ext}"
            filepath = os.path.join(posters_dir, filename)

            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
                with urllib.request.urlopen(req, timeout=10) as res, open(filepath, 'wb') as f:
                    f.write(res.read())
                
                local_url = f"/media/movies/posters/{filename}"
                movies = Movie.objects.filter(title__icontains=title.split(':')[0].strip())
                for movie in movies:
                    movie.poster_path = local_url
                    movie.tmdb_poster_url = local_url
                    movie.save()
                self.stdout.write(self.style.SUCCESS(f"Saved local poster for {title} -> {local_url}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not download local poster for {title}: {e}"))
