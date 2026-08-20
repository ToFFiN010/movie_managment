import os
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie

class Command(BaseCommand):
    help = 'Inspects every Movie, matches the correct poster artwork, and attaches it to the database.'

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        posters_dir = media_root / 'posters'
        movies_posters_dir = media_root / 'movies' / 'posters'

        movies = Movie.objects.all()
        ok_count = 0
        fixed_count = 0
        missing_count = 0

        for movie in movies:
            slug = movie.slug
            # Candidates for poster artwork (prioritizing high quality images in media/posters/ and media/movies/posters/)
            candidates = [
                f"posters/{slug}_poster.jpg",
                f"posters/{slug}_poster.png",
                f"posters/{slug}.jpg",
                f"posters/{slug}.png",
                f"movies/posters/{slug}.jpg",
                f"movies/posters/{slug}.png",
                f"movies/posters/{slug}_poster.jpg",
            ]

            found_path = None
            for candidate in candidates:
                abs_path = media_root / candidate
                if abs_path.exists() and abs_path.stat().st_size > 0:
                    # Verify it's not a 0-byte or corrupted file
                    found_path = candidate
                    break

            if not found_path:
                self.stdout.write(f"[MISSING] {movie.title}")
                missing_count += 1
                continue

            current_poster = movie.poster.name if movie.poster else ""
            
            # Check if currently attached poster is valid and equal to found_path
            current_abs_path = media_root / current_poster if current_poster else None
            
            if current_poster == found_path and current_abs_path and current_abs_path.exists():
                self.stdout.write(f"[OK] {movie.title}")
                ok_count += 1
            else:
                movie.poster.name = found_path
                # Also set tmdb_poster_url or poster_path if empty
                if not movie.poster_path:
                    movie.poster_path = f"/media/{found_path}"
                movie.save(update_fields=['poster', 'poster_path'])
                self.stdout.write(f"[FIXED] {movie.title}")
                fixed_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: {ok_count} OK, {fixed_count} FIXED, {missing_count} MISSING out of {movies.count()} total movies."
            )
        )
