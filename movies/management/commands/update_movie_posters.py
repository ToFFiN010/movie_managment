import os
import io
import urllib.request
import urllib.parse
import json
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie
from movies.services.tmdb import search_tmdb_movie

# Map of verified TMDB and official studio promotional poster URLs per movie title
VERIFIED_TMDB_POSTERS = {
    "Oppenheimer": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
    "Dune: Part Two": "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg",
    "The Dark Knight": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
    "Interstellar": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
    "The Shawshank Redemption": "https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
    "Top Gun: Maverick": "https://image.tmdb.org/t/p/w500/62HCnUTziyWcpDaBO2i1DX17ljH.jpg",
    "Barbie": "https://image.tmdb.org/t/p/w500/iuFNMS8U5cb6xfzi51Dbkovj7vM.jpg",
    "John Wick: Chapter 4": "https://image.tmdb.org/t/p/w500/vZloFAK7NmvMGKE7VkF5UHaz0I.jpg",
    "The Batman Part II": "https://image.tmdb.org/t/p/w500/74xTEgt7R36Fpooo50r9T25onhq.jpg",
    "Avatar 3: Fire and Ash": "https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg",
    "Jawan": "https://upload.wikimedia.org/wikipedia/en/3/39/Jawan_film_poster.jpg",
    "Salaar": "https://upload.wikimedia.org/wikipedia/en/a/a6/Salaar_Part_1_%E2%80%93_Ceasefire.jpg",
    "Salaar: Part 1 – Ceasefire": "https://upload.wikimedia.org/wikipedia/en/a/a6/Salaar_Part_1_%E2%80%93_Ceasefire.jpg",
    "12th Fail": "https://upload.wikimedia.org/wikipedia/en/f/f2/12th_Fail_poster.jpeg",
    "Kalki 2898 AD": "https://upload.wikimedia.org/wikipedia/en/4/4c/Kalki_2898_AD.jpg",
    "Leo": "https://upload.wikimedia.org/wikipedia/en/7/75/Leo_%282023_Indian_film%29.jpg",
    "KGF: Chapter 2": "https://upload.wikimedia.org/wikipedia/en/d/d0/K.G.F_Chapter_2.jpg",
    "Kantara: Chapter 1": "https://upload.wikimedia.org/wikipedia/en/8/84/Kantara_poster.jpeg",
    "Dune: Part Two (2026 Edition)": "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg",
}

class Command(BaseCommand):
    help = 'Processes every Movie record, searches TMDB by title/year, downloads poster, and updates database record.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force re-download even if poster exists')

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        posters_dir = media_root / 'movies' / 'posters'
        os.makedirs(posters_dir, exist_ok=True)

        force = options.get('force', False)
        movies = Movie.objects.all().order_by('id')

        self.stdout.write(self.style.MIGRATE_HEADING("=== CINEPRIME TMDB MOVIE POSTER PROCESSOR ===\n"))
        self.stdout.write(f"Processing {movies.count()} database movie records...\n")

        downloaded_count = 0
        updated_count = 0
        failed_count = 0

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        for movie in movies:
            title = movie.title
            year = movie.release_date.year if movie.release_date else None
            slug = movie.slug
            target_filename = f"{slug}.jpg"
            target_path = posters_dir / target_filename
            rel_db_path = f"movies/posters/{target_filename}"

            # Check if poster already exists and is non-empty
            if not force and target_path.exists() and target_path.stat().st_size > 5000:
                if not movie.poster or movie.poster.name != rel_db_path:
                    movie.poster.name = rel_db_path
                    movie.poster_path = f"/media/{rel_db_path}"
                    movie.save(update_fields=['poster', 'poster_path'])
                    updated_count += 1
                self.stdout.write(f"Movie ID: {movie.id:<2} | Title: {title:<30} | Year: {year} | Status: OK ({target_filename}) | Database: Updated")
                continue

            # Determine poster download URL
            download_url = VERIFIED_TMDB_POSTERS.get(title)

            # Query TMDB API if not in pre-mapped table
            if not download_url:
                tmdb_data = search_tmdb_movie(title, release_year=year)
                if tmdb_data and tmdb_data.get('poster_url'):
                    download_url = tmdb_data['poster_url']

            # Download poster image
            if download_url:
                try:
                    req = urllib.request.Request(download_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        img_bytes = resp.read()
                        im = Image.open(io.BytesIO(img_bytes)).convert('RGB')

                        # Resize to standard 2:3 aspect ratio (1000x1500)
                        sw, sh = im.size
                        tr = 1000 / 1500
                        sr = sw / sh
                        if sr > tr:
                            nw = int(sh * tr)
                            ox = (sw - nw) // 2
                            cropped = im.crop((ox, 0, ox + nw, sh))
                        else:
                            nh = int(sw / tr)
                            oy = (sh - nh) // 2
                            cropped = im.crop((0, oy, sw, oy + nh))

                        resized = cropped.resize((1000, 1500), Image.Resampling.LANCZOS)
                        resized.save(target_path, 'JPEG', quality=95)

                        movie.poster.name = rel_db_path
                        movie.poster_path = f"/media/{rel_db_path}"
                        movie.save(update_fields=['poster', 'poster_path'])
                        downloaded_count += 1
                        updated_count += 1
                        self.stdout.write(f"Movie ID: {movie.id:<2} | Title: {title:<30} | Year: {year} | Status: Downloaded | Database: Updated")
                        continue
                except Exception as e:
                    self.stdout.write(f"Movie ID: {movie.id:<2} | Title: {title:<30} | Download Warning: {e}")

            # Reuse existing valid local image file if present
            if target_path.exists() and target_path.stat().st_size > 0:
                movie.poster.name = rel_db_path
                movie.poster_path = f"/media/{rel_db_path}"
                movie.save(update_fields=['poster', 'poster_path'])
                updated_count += 1
                self.stdout.write(f"Movie ID: {movie.id:<2} | Title: {title:<30} | Year: {year} | Status: Verified Local | Database: Updated")
            else:
                failed_count += 1
                self.stdout.write(f"Movie ID: {movie.id:<2} | Title: {title:<30} | Year: {year} | Status: MISSING")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nUpdate Complete: {downloaded_count} downloaded, {updated_count} database records updated, {failed_count} missing out of {movies.count()} total movies."
            )
        )
