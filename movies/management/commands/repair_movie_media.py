import os
import io
import re
import urllib.request
import urllib.parse
from difflib import SequenceMatcher
from PIL import Image, ImageDraw
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from movies.models import Movie
from movies.services.tmdb import search_tmdb_movie, TMDB_POSTER_BASE

LOG_DIR = os.path.join(settings.BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'movie_media.log')

def log_media_event(movie_id, title, source, status, reason=''):
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] MEDIA_REPAIR movie_id={movie_id} title=\"{title}\" source=\"{source}\" status=\"{status}\" reason=\"{reason}\"\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def calculate_title_similarity(a, b):
    a_norm = re.sub(r'[^\w\s]', '', a.lower()).strip()
    b_norm = re.sub(r'[^\w\s]', '', b.lower()).strip()
    return SequenceMatcher(None, a_norm, b_norm).ratio()

def generate_cineprime_fallback(title, release_year, target_path):
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    width, height = 600, 900
    img = Image.new('RGB', (width, height), color='#090D16')
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, width, height], outline='#FFB000', width=8)
    draw.rectangle([16, 16, width - 16, height - 16], outline='#1F2937', width=3)

    draw.text((width // 2, 80), "CINEPRIME", fill="#FFB000", anchor="mm")
    draw.line([(100, 110), (width - 100, 110)], fill="#3B82F6", width=2)

    words = title.split()
    lines = []
    current = []
    for w in words:
        current.append(w)
        if len(' '.join(current)) > 16:
            lines.append(' '.join(current[:-1]))
            current = [w]
    if current:
        lines.append(' '.join(current))

    start_y = 380 - (len(lines) * 25)
    for i, line in enumerate(lines[:4]):
        draw.text((width // 2, start_y + (i * 50)), line.upper(), fill="#FFFFFF", anchor="mm")

    draw.rectangle([width // 2 - 80, start_y + (len(lines) * 50) + 20, width // 2 + 80, start_y + (len(lines) * 50) + 60], fill="#1E293B", outline="#475569")
    draw.text((width // 2, start_y + (len(lines) * 50) + 40), f"RELEASE: {release_year}", fill="#94A3B8", anchor="mm")

    draw.rectangle([width // 2 - 120, height - 120, width // 2 + 120, height - 80], fill="#334155")
    draw.text((width // 2, height - 100), "POSTER UNAVAILABLE", fill="#F8FAFC", anchor="mm")

    img.save(target_path, 'JPEG', quality=90)
    return target_path


class Command(BaseCommand):
    help = 'Bulk repairs movie posters using TMDb API with title/year confidence matching, metadata tracking, and CinePrime fallbacks.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force re-repair of existing valid posters.')

    def handle(self, *args, **options):
        force = options.get('force', False)
        self.stdout.write("\nStarting CinePrime Bulk Movie Poster Repair Pipeline...\n")

        movies = Movie.objects.all().order_by('id')
        total = movies.count()

        posters_added = 0
        already_valid = 0
        fallbacks_created = 0
        manual_reviews = 0

        posters_dir = os.path.join(settings.MEDIA_ROOT, 'movies', 'posters')
        os.makedirs(posters_dir, exist_ok=True)

        for idx, movie in enumerate(movies, start=1):
            title = movie.title.strip()
            year = movie.release_year
            slug = movie.slug or f"movie-{movie.id}"

            self.stdout.write(f"Processing {idx}/{total}:")
            self.stdout.write(f"{title} ({year})")

            if not force and movie.poster:
                try:
                    if os.path.exists(movie.poster.path) and os.path.getsize(movie.poster.path) > 1000:
                        if getattr(movie, 'poster_source', '') != 'placeholder':
                            already_valid += 1
                            self.stdout.write(self.style.SUCCESS("  [OK] Poster already valid"))
                            self.stdout.write("")
                            continue
                except Exception:
                    pass

            tmdb_data = search_tmdb_movie(title, release_year=year)
            repaired = False

            if tmdb_data and tmdb_data.get('poster_url'):
                tmdb_title = tmdb_data.get('title') or title
                tmdb_id = str(tmdb_data.get('tmdb_id', ''))
                poster_url = tmdb_data['poster_url']

                sim_score = calculate_title_similarity(title, tmdb_title)

                # Confidence rule check: Similarity >= 85%
                if sim_score >= 0.85:
                    self.stdout.write(self.style.SUCCESS(f"  [OK] TMDb match found (Confidence: {round(sim_score * 100)}%, ID: {tmdb_id})"))
                    
                    # Download image payload
                    try:
                        req = urllib.request.Request(poster_url, headers={'User-Agent': 'CinePrime/1.0'})
                        with urllib.request.urlopen(req, timeout=8) as res:
                            if res.status == 200 and 'image' in res.headers.get('Content-Type', ''):
                                data = res.read()
                                if len(data) > 100:
                                    img = Image.open(io.BytesIO(data))
                                    img.verify()

                                    img = Image.open(io.BytesIO(data))
                                    if img.mode != 'RGB':
                                        img = img.convert('RGB')

                                    target_filename = f"{slug}.jpg"
                                    target_full_path = os.path.join(posters_dir, target_filename)

                                    img_resized = img.resize((600, 900), Image.Resampling.LANCZOS)
                                    img_resized.save(target_full_path, 'JPEG', quality=88, optimize=True)

                                    rel_path = f"movies/posters/{target_filename}"
                                    movie.poster = rel_path
                                    movie.image_source = "TMDB"
                                    movie.image_source_id = tmdb_id
                                    movie.image_source_url = poster_url
                                    movie.poster_source = "tmdb"
                                    movie.poster_source_url = poster_url
                                    movie.poster_source_id = tmdb_id
                                    movie.poster_verified = True
                                    movie.media_status = "ok"
                                    movie.poster_last_checked = timezone.now()
                                    movie.save()

                                    repaired = True
                                    posters_added += 1
                                    self.stdout.write(self.style.SUCCESS("  [OK] Poster attached"))
                                    log_media_event(movie.id, title, "TMDB", "success", f"Attached TMDb ID {tmdb_id}")
                    except Exception as e:
                        log_media_event(movie.id, title, "TMDB", "failed", f"Download error: {e}")
                else:
                    self.stdout.write(self.style.WARNING(f"  [WARN] Low confidence match ({round(sim_score * 100)}%) -> Manual review required"))
                    movie.media_status = "manual_review"
                    movie.save()
                    manual_reviews += 1
                    log_media_event(movie.id, title, "TMDB", "manual_review", f"Low title similarity: {round(sim_score * 100)}%")
            else:
                log_media_event(movie.id, title, "TMDB", "failed", "No TMDb search result returned")

            # Fallback generator if TMDb match was unconfident or failed
            if not repaired and movie.media_status != "manual_review":
                target_filename = f"{slug}_fallback.jpg"
                target_full_path = os.path.join(posters_dir, target_filename)
                generate_cineprime_fallback(title, year, target_full_path)

                rel_path = f"movies/posters/{target_filename}"
                movie.poster = rel_path
                movie.poster_source = "placeholder"
                movie.image_source = "CINEPRIME_FALLBACK"
                movie.poster_verified = False
                movie.poster_last_checked = timezone.now()
                movie.save()

                fallbacks_created += 1
                self.stdout.write(self.style.WARNING("  -> Fallback poster created"))

            self.stdout.write("")

        summary_str = f"""
========================================
BULK REPAIR FINAL REPORT
========================================
{total} movies processed
{posters_added} posters added
{already_valid} posters already valid
{fallbacks_created} fallback posters created
{manual_reviews} manual review required
========================================
"""
        self.stdout.write(summary_str)
