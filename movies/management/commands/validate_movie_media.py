import os
import json
import urllib.request
import urllib.error
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie
from movies.utils import get_youtube_video_id

class Command(BaseCommand):
    help = 'Validates image integrity, file existence, and YouTube trailer embed reachability for all movies.'

    def handle(self, *args, **options):
        self.stdout.write("\nStarting CinePrime Movie Media Validation Pipeline...\n")

        movies = Movie.objects.all().order_by('id')
        total = movies.count()

        valid_posters = 0
        broken_posters = 0
        valid_trailers = 0
        broken_trailers = 0

        for movie in movies:
            poster_ok = False
            if movie.poster:
                try:
                    p_path = movie.poster.path
                    if os.path.exists(p_path) and os.path.getsize(p_path) > 0:
                        with Image.open(p_path) as img:
                            img.verify()
                        poster_ok = True
                        valid_posters += 1
                except Exception:
                    pass

            if not poster_ok:
                broken_posters += 1

            trailer_ok = False
            vid = get_youtube_video_id(movie.trailer_url or movie.youtube_video_id)
            if vid and len(vid) == 11:
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
                try:
                    req = urllib.request.Request(oembed_url, headers={'User-Agent': 'CinePrime/1.0'})
                    with urllib.request.urlopen(req, timeout=4) as response:
                        if response.status == 200:
                            trailer_ok = True
                            valid_trailers += 1
                except Exception:
                    pass

            if not trailer_ok:
                broken_trailers += 1

            self.stdout.write(f"#{movie.id} {movie.title} | Poster: {'[OK]' if poster_ok else '[FAIL]'} | Trailer: {'[OK]' if trailer_ok else '[FAIL]'}")

        summary_str = f"""
========================================
MEDIA VALIDATION REPORT
========================================
Total Movies Inspected:   {total}

Valid Posters:            {valid_posters}
Broken / Missing Posters: {broken_posters}
Valid YouTube Trailers:   {valid_trailers}
Broken / Missing Trailers:{broken_trailers}
========================================
"""
        self.stdout.write(summary_str)
