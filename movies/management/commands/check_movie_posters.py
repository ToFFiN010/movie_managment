import os
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie

class Command(BaseCommand):
    help = 'Audits and checks poster image status for every movie in the database.'

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        movies = Movie.objects.all().order_by('id')

        ok_count = 0
        missing_count = 0

        self.stdout.write("========================================")
        self.stdout.write("CINEPRIME POSTER CHECK")
        self.stdout.write("========================================\n")

        for movie in movies:
            poster = movie.poster

            if not poster or not poster.name:
                self.stdout.write(f"{movie.title:<30} MISSING")
                missing_count += 1
                continue

            rel_path = poster.name
            abs_path = media_root / rel_path

            if abs_path.exists() and abs_path.stat().st_size > 0:
                self.stdout.write(f"{movie.title:<30} OK POSTER")
                ok_count += 1
            else:
                self.stdout.write(f"{movie.title:<30} MISSING")
                missing_count += 1

        self.stdout.write("\n========================================")
        self.stdout.write(f"TOTAL MOVIES: {movies.count()}")
        self.stdout.write(f"POSTERS FOUND: {ok_count}")
        self.stdout.write(f"MISSING POSTERS: {missing_count}")
        self.stdout.write("========================================\n")
