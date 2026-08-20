import os
import io
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from movies.models import Movie
from movies.services.tmdb import search_tmdb_movie

LOG_DIR = settings.BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'movie_image_failures.log'

def log_failure(movie_id, title, release_year, path_or_url, reason, http_status=None):
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = (
        f"[{timestamp}] Movie ID #{movie_id} | '{title}' ({release_year}) | "
        f"Path/URL: {path_or_url} | Reason: {reason} | HTTP Status: {http_status or 'N/A'}\n"
    )
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def generate_safe_placeholder(movie, target_path):
    """
    Generates a safe fallback placeholder containing:
    - movie title
    - release year
    - movie icon
    """
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    width, height = 500, 750
    img = Image.new('RGB', (width, height), color='#0F172A')
    draw = ImageDraw.Draw(img)

    # Stylish gold borders
    draw.rectangle([10, 10, width - 10, height - 10], outline='#FFB000', width=4)
    draw.rectangle([18, 18, width - 18, height - 18], outline='#334155', width=2)

    # Brand header
    draw.text((width // 2, 60), "CINEPRIME", fill="#FFB000", anchor="mm")
    draw.line([(80, 85), (width - 80, 85)], fill="#3B82F6", width=2)

    # Movie Icon symbol placeholder (Film reel / camera box)
    icon_box = [width // 2 - 40, height // 3 - 40, width // 2 + 40, height // 3 + 40]
    draw.rectangle(icon_box, fill="#1E293B", outline="#FFB000", width=3)
    draw.text((width // 2, height // 3), "🎬", fill="#FFFFFF", anchor="mm")

    # Title word wrap
    words = movie.title.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(' '.join(current_line)) > 18:
            lines.append(' '.join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    start_y = height // 2 + 10
    for i, line in enumerate(lines[:3]):
        draw.text((width // 2, start_y + (i * 40)), line.upper(), fill="#FFFFFF", anchor="mm")

    # Release year & Director info
    meta_y = start_y + (len(lines[:3]) * 40) + 20
    draw.rectangle([width // 2 - 100, meta_y, width // 2 + 100, meta_y + 36], fill="#1E293B", outline="#475569")
    draw.text((width // 2, meta_y + 18), f"RELEASE: {movie.release_year}", fill="#94A3B8", anchor="mm")

    # Footer note
    draw.text((width // 2, height - 50), "POSTER UNAVAILABLE", fill="#64748B", anchor="mm")

    img.save(target_path, 'JPEG', quality=88)
    return target_path


def validate_image_file(file_path_or_bytes):
    """
    Validates image:
    - Supported formats: JPG, JPEG, PNG, WebP
    - File size > 1KB
    - Dimensions check
    - Non-corrupted PIL integrity
    """
    if isinstance(file_path_or_bytes, (str, os.PathLike)):
        p = os.fspath(file_path_or_bytes)
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            return False, "File missing or under 1KB"
        with open(p, 'rb') as f:
            data = f.read()
    else:
        data = file_path_or_bytes

    if len(data) < 1000:
        return False, "Payload under 1KB"

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()

        # Re-open for mode/dimensions check
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or '').upper()
        if fmt not in ['JPEG', 'JPG', 'PNG', 'WEBP']:
            return False, f"Unsupported image format: {fmt}"

        w, h = img.size
        if w < 100 or h < 100:
            return False, f"Image dimensions too small: {w}x{h}"

        return True, "Valid"
    except Exception as e:
        return False, f"Corrupted image payload ({e})"


class Command(BaseCommand):
    help = 'Repairs missing/broken/placeholder movie posters. Never overwrites existing valid posters.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force repair and re-process existing posters.')

    def handle(self, *args, **options):
        force = options.get('force', False)

        self.stdout.write("\n================================================================================")
        self.stdout.write("                CINEPRIME AUTOMATIC MOVIE POSTER REPAIR                        ")
        self.stdout.write("================================================================================\n")

        posters_dir = settings.MEDIA_ROOT / 'movies' / 'posters'
        os.makedirs(posters_dir, exist_ok=True)

        movies = Movie.objects.all().order_by('id')
        total = movies.count()

        repaired_cnt = 0
        existing_ok_cnt = 0
        placeholder_cnt = 0
        failed_cnt = 0

        for movie in movies:
            title = movie.title.strip()
            year = movie.release_year
            slug = movie.slug or f"movie-{movie.id}"
            poster_field = movie.poster.name if movie.poster else ""

            # Check if valid non-placeholder poster already exists
            if not force and movie.poster and poster_field:
                if getattr(movie, 'poster_source', '') != 'placeholder' and not poster_field.endswith('_fallback.jpg'):
                    abs_p = settings.MEDIA_ROOT / poster_field
                    is_valid, reason = validate_image_file(abs_p)
                    if is_valid:
                        existing_ok_cnt += 1
                        self.stdout.write(self.style.SUCCESS(f"[SKIP] #{movie.id:2d} '{title}' already has a valid poster: {poster_field}"))
                        continue

            self.stdout.write(f"\n[REPAIRING] #{movie.id:2d} '{title}' ({year})...")

            # 1. Search for existing authentic local poster files on disk first
            target_filename = f"movie_{movie.id}_poster.webp"
            target_full_path = posters_dir / target_filename
            saved_relative_path = None
            found_local_file = None

            local_candidates = [
                posters_dir / f"{slug}-poster.webp",
                posters_dir / f"{slug}-poster.jpg",
                posters_dir / f"{slug}.webp",
                posters_dir / f"{slug}.jpg",
                posters_dir / f"{slug}_poster.png",
                posters_dir / f"movie_{movie.id}_poster.webp",
            ]

            for cand_path in local_candidates:
                if cand_path.exists() and not cand_path.name.endswith('_fallback.jpg'):
                    is_val, rsn = validate_image_file(cand_path)
                    if is_val:
                        found_local_file = cand_path
                        self.stdout.write(f"  Found authentic local poster file: {cand_path.name}")
                        break

            if found_local_file:
                try:
                    img = Image.open(found_local_file)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img_resized = img.resize((500, 750), Image.Resampling.LANCZOS)
                    img_resized.save(target_full_path, 'WEBP', quality=85, optimize=True)

                    saved_relative_path = f"movies/posters/{target_filename}"
                    movie.poster = saved_relative_path
                    movie.poster_source = 'local_authentic'
                    movie.poster_verified = True
                    movie.poster_last_checked = timezone.now()
                    movie.save()
                    repaired_cnt += 1
                    self.stdout.write(self.style.SUCCESS(f"  [OK] Repaired & Standardized local poster for '{title}' -> {saved_relative_path}"))
                    continue
                except Exception as e:
                    log_failure(movie.id, title, year, str(found_local_file), f"Failed processing local poster ({e})")

            # 2. Query TMDB API or TMDB curated fallback map
            tmdb_data = search_tmdb_movie(title, release_year=year)
            download_url = None
            source_id = ''

            if tmdb_data and tmdb_data.get('poster_url'):
                download_url = tmdb_data['poster_url']
                source_id = str(tmdb_data.get('tmdb_id', ''))
                self.stdout.write(f"  Found TMDB match: ID {source_id} -> {download_url}")

            # If download_url starts with /media/, it's a local relative poster path from curated map
            if download_url and download_url.startswith('/media/'):
                rel_clean = download_url.lstrip('/media/')
                abs_mapped = settings.MEDIA_ROOT / rel_clean
                is_val, rsn = validate_image_file(abs_mapped)
                if is_val:
                    try:
                        img = Image.open(abs_mapped)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img_resized = img.resize((500, 750), Image.Resampling.LANCZOS)
                        img_resized.save(target_full_path, 'WEBP', quality=85, optimize=True)

                        saved_relative_path = f"movies/posters/{target_filename}"
                        movie.poster = saved_relative_path
                        movie.poster_source = 'tmdb'
                        movie.poster_source_id = source_id
                        movie.poster_verified = True
                        movie.poster_last_checked = timezone.now()
                        movie.save()
                        repaired_cnt += 1
                        self.stdout.write(self.style.SUCCESS(f"  [OK] Linked Curated TMDB Poster for '{title}' -> {saved_relative_path}"))
                        continue
                    except Exception as e:
                        log_failure(movie.id, title, year, download_url, f"Failed converting curated image ({e})")
                else:
                    log_failure(movie.id, title, year, download_url, f"Curated path invalid ({rsn})")
                    download_url = None

            # If download_url is an external HTTP URL
            if download_url and (download_url.startswith('http://') or download_url.startswith('https://')):
                try:
                    req = urllib.request.Request(download_url, headers={'User-Agent': 'CinePrime/1.0'})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        http_code = resp.status
                        content_type = resp.headers.get('Content-Type', '')

                        if http_code == 200 and 'image' in content_type:
                            img_data = resp.read()
                            is_val, rsn = validate_image_file(img_data)
                            if is_val:
                                img = Image.open(io.BytesIO(img_data))
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')

                                img_resized = img.resize((500, 750), Image.Resampling.LANCZOS)
                                img_resized.save(target_full_path, 'WEBP', quality=85, optimize=True)

                                saved_relative_path = f"movies/posters/{target_filename}"
                                movie.poster = saved_relative_path
                                movie.poster_source = 'tmdb'
                                movie.poster_source_url = download_url
                                movie.poster_source_id = source_id
                                movie.poster_verified = True
                                movie.poster_last_checked = timezone.now()
                                if tmdb_data and tmdb_data.get('tmdb_id'):
                                    movie.tmdb_id = tmdb_data['tmdb_id']
                                    movie.poster_path = tmdb_data.get('poster_path')

                                movie.save()
                                repaired_cnt += 1
                                self.stdout.write(self.style.SUCCESS(f"  [OK] Downloaded & Standardized TMDB poster for '{title}' -> {saved_relative_path}"))
                                continue
                            else:
                                log_failure(movie.id, title, year, download_url, f"Downloaded image invalid ({rsn})", http_code)
                        else:
                            log_failure(movie.id, title, year, download_url, f"HTTP non-200 or non-image content", http_code)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  [FAIL] Failed downloading TMDB poster: {e}"))
                    log_failure(movie.id, title, year, download_url, f"Download exception: {e}", 500)

            # 3. Fallback placeholder generator if no authentic poster available
            fallback_filename = f"movie_{movie.id}_poster_fallback.jpg"
            fallback_full_path = posters_dir / fallback_filename
            generate_safe_placeholder(movie, fallback_full_path)

            saved_relative_path = f"movies/posters/{fallback_filename}"
            movie.poster = saved_relative_path
            movie.poster_source = 'placeholder'
            movie.poster_verified = False
            movie.poster_last_checked = timezone.now()
            movie.save()
            placeholder_cnt += 1
            log_failure(movie.id, title, year, saved_relative_path, "No verified authentic poster found, safe fallback placeholder generated")
            self.stdout.write(self.style.WARNING(f"  [WARN] Built Safe Fallback Placeholder for '{title}' -> {saved_relative_path}"))

        summary_str = f"""
================================================================================
                    IMAGE REPAIR SUMMARY REPORT
================================================================================
Total Movies Processed  : {total}
Existing Valid Posters  : {existing_ok_cnt}
Posters Repaired        : {repaired_cnt}
Fallbacks Built         : {placeholder_cnt}
Failure Log File        : logs/movie_image_failures.log
================================================================================
"""
        self.stdout.write(summary_str)
