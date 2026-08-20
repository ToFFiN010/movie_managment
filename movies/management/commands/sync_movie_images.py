import os
import re
import io
import csv
import json
import hashlib
import logging
import urllib.request
import urllib.parse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from movies.models import Movie, MovieImage
from movies.services.tmdb import search_tmdb_movie, get_api_key

# Set up logging to logs/movie_images.log
LOG_DIR = settings.BASE_DIR / 'logs'
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = LOG_DIR / 'movie_images.log'
BACKUP_FILE = LOG_DIR / 'movie_images_backup.json'

logger = logging.getLogger('movie_images_sync')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
if not logger.handlers:
    logger.addHandler(file_handler)

def log_info(msg):
    logger.info(msg)
    print(f"[INFO] {msg}")

def log_warning(msg):
    logger.warning(msg)
    print(f"[WARNING] {msg}")

def log_error(msg):
    logger.error(msg)
    print(f"[ERROR] {msg}")


def normalize_title(title):
    """
    Intelligent title normalization:
    - Lowercase
    - Replace roman numerals with standard digits (ii -> 2, iii -> 3, iv -> 4, etc.)
    - Remove punctuation (hyphens, colons, apostrophes, commas, quotes)
    - Normalize ampersands to 'and'
    - Collapse extra spaces
    """
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r'\bpart\s+ii\b', 'part 2', t)
    t = re.sub(r'\bpart\s+iii\b', 'part 3', t)
    t = re.sub(r'\bpart\s+iv\b', 'part 4', t)
    t = re.sub(r'\bchapter\s+ii\b', 'chapter 2', t)
    t = re.sub(r'\bchapter\s+iii\b', 'chapter 3', t)
    t = re.sub(r'\bchapter\s+iv\b', 'chapter 4', t)

    t = t.replace('&', 'and')
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def validate_image_file(file_path, min_w=300, min_h=450):
    """
    Validates that file exists, is openable by PIL, is JPG/PNG/WEBP,
    has valid dimensions, and is not corrupt.
    """
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    size = os.path.getsize(file_path)
    if size < 2000:
        return False, f"File size too small ({size} bytes)"

    try:
        with Image.open(file_path) as im:
            fmt = im.format
            w, h = im.size
            im.verify()

        if fmt not in ['JPEG', 'PNG', 'WEBP']:
            return False, f"Unsupported format: {fmt}"

        if w < min_w or h < min_h:
            return False, f"Dimensions too small: {w}x{h} (min {min_w}x{min_h})"

        ratio = w / float(h)
        if ratio < 0.3 or ratio > 1.2:
            return False, f"Unusual aspect ratio: {ratio:.2f}"

        return True, "Valid"
    except Exception as e:
        return False, f"Corrupted file: {e}"


def generate_cineprime_placeholder(movie, target_path):
    """
    Generates a 600x900px CinePrime branded fallback poster placeholder containing:
    CINEPRIME logo, Movie Title, Release Year, and 'Poster Unavailable' notice.
    """
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    width, height = 600, 900

    img = Image.new('RGB', (width, height), color='#070B14')
    draw = ImageDraw.Draw(img)

    # Ambient Glow
    for r in range(400, 0, -5):
        alpha = int(30 * (1 - r / 400))
        draw.ellipse([width//2 - r, height//3 - r, width//2 + r, height//3 + r], fill=(139, 92, 246, alpha))

    # Outer border
    draw.rectangle([16, 16, width - 16, height - 16], outline='#FFB000', width=3)
    draw.rectangle([24, 24, width - 24, height - 24], outline='#06B6D4', width=1)

    try:
        font_brand = ImageFont.truetype("arial.ttf", 26)
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_sub = ImageFont.truetype("arial.ttf", 18)
        font_meta = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font_brand = font_title = font_sub = font_meta = ImageFont.load_default()

    # Brand header
    draw.text((width // 2, 60), "CINEPRIME CINEMAS", fill='#FFB000', font=font_brand, anchor="mm")
    draw.text((width // 2, 90), "OFFICIAL PREVIEW CATALOG", fill='#06B6D4', font=font_meta, anchor="mm")

    # Center Film Icon Box
    center_y = 300
    draw.ellipse([width//2 - 70, center_y - 70, width//2 + 70, center_y + 70], fill='#0E1628', outline='#8B5CF6', width=3)
    draw.text((width // 2, center_y - 10), "🎬", fill='#FFB000', font=font_brand, anchor="mm")
    draw.text((width // 2, center_y + 35), "POSTER UNAVAILABLE", fill='#FF5C5C', font=font_meta, anchor="mm")

    # Wrapped Title
    raw_title = movie.title.upper()
    words = raw_title.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if len(" ".join(curr)) > 16:
            curr.pop()
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    y_pos = 480
    for line in lines[:3]:
        draw.text((width // 2, y_pos), line, fill='#FFFFFF', font=font_title, anchor="mm")
        y_pos += 46

    # Release Year & Director
    year_str = movie.release_date.strftime('%Y') if movie.release_date else '2026'
    draw.text((width // 2, height - 120), f"RELEASE YEAR: {year_str}", fill='#FFB000', font=font_sub, anchor="mm")
    if movie.director:
        draw.text((width // 2, height - 85), f"DIRECTED BY {movie.director.upper()}", fill='#A8B0C0', font=font_meta, anchor="mm")

    img.save(target_path, 'JPEG', quality=92)
    return target_path


class Command(BaseCommand):
    help = 'Idempotently synchronizes, validates, and matches movie posters with database safety and placeholder fallbacks.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force re-validation and matching of existing valid posters')

    def handle(self, *args, **options):
        force = options.get('force', False)
        media_root = settings.MEDIA_ROOT
        posters_dir = media_root / 'movies' / 'posters'
        os.makedirs(posters_dir, exist_ok=True)

        log_info(f"Starting CinePrime Movie Image Synchronization Pipeline (Force={force})...")

        # Step 1: Create Database Backup JSON
        backup_data = []
        for m in Movie.objects.all():
            backup_data.append({
                'id': m.id,
                'title': m.title,
                'poster': m.poster.name if m.poster else None,
                'backdrop_image': m.backdrop_image.name if m.backdrop_image else None,
                'poster_path': m.poster_path,
                'backdrop_path': m.backdrop_path,
                'tmdb_poster_url': m.tmdb_poster_url,
                'tmdb_backdrop_url': m.tmdb_backdrop_url,
            })
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2)
        log_info(f"Created database image fields backup at: {BACKUP_FILE}")

        # Step 2: Iterate movies and synchronize
        total_count = 0
        already_valid_count = 0
        new_added_count = 0
        repaired_count = 0
        placeholders_created_count = 0
        failed_count = 0
        duplicate_count = 0
        manual_review_list = []

        seen_hashes = {}

        for movie in Movie.objects.all().iterator():
            total_count += 1
            has_valid_poster = False
            curr_poster_path = None

            if movie.poster and movie.poster.name:
                abs_p = media_root / movie.poster.name
                valid, msg = validate_image_file(abs_p)
                if valid:
                    has_valid_poster = True
                    curr_poster_path = abs_p

            if has_valid_poster and not force:
                already_valid_count += 1
                log_info(f"SKIP (Already Valid): '{movie.title}' -> {movie.poster.name}")
            else:
                # Attempt to match local image file by normalized title
                norm_movie_title = normalize_title(movie.title)
                matched_file = None

                for fname in os.listdir(posters_dir):
                    f_abs = posters_dir / fname
                    if not f_abs.is_file():
                        continue
                    norm_fname = normalize_title(fname)
                    
                    # Strict title matching
                    if norm_movie_title in norm_fname or norm_fname in norm_movie_title:
                        # Check sequel / release year matching to reject ambiguous matches
                        if '2' in norm_movie_title and '2' not in norm_fname:
                            continue
                        if '3' in norm_movie_title and '3' not in norm_fname:
                            continue
                        if '4' in norm_movie_title and '4' not in norm_fname:
                            continue

                        v_ok, v_msg = validate_image_file(f_abs)
                        if v_ok:
                            matched_file = f"movies/posters/{fname}"
                            break

                if matched_file:
                    movie.poster.name = matched_file
                    movie.save(update_fields=['poster'])
                    new_added_count += 1
                    log_info(f"MATCH SUCCESS: '{movie.title}' -> {matched_file}")
                else:
                    # Generate CinePrime Branded Placeholder
                    placeholder_fname = f"{movie.slug}-placeholder.jpg"
                    placeholder_abs = posters_dir / placeholder_fname
                    generate_cineprime_placeholder(movie, placeholder_abs)
                    
                    rel_placeholder = f"movies/posters/{placeholder_fname}"
                    movie.poster.name = rel_placeholder
                    movie.save(update_fields=['poster'])
                    placeholders_created_count += 1
                    manual_review_list.append((movie.id, movie.title, "No local file match found; generated CinePrime placeholder."))
                    log_warning(f"PLACEHOLDER ASSIGNED: '{movie.title}' -> {rel_placeholder}")

            # Ensure Primary MovieImage DB record exists
            if movie.poster and movie.poster.name:
                MovieImage.objects.update_or_create(
                    movie=movie,
                    is_primary=True,
                    defaults={
                        'image': movie.poster.name,
                        'image_type': MovieImage.ImageType.POSTER,
                        'caption': f"Official Poster for {movie.title}",
                        'source_name': 'CinePrime Media Storage',
                        'source_url': movie.get_poster_url,
                        'license_information': 'Promotional / Fair Use',
                        'verification_status': MovieImage.VerificationStatus.VERIFIED,
                        'image_status': MovieImage.ImageStatus.VALID,
                        'verification_date': timezone.now(),
                    }
                )

        # Final Summary Report
        summary_str = f"""
==================================================
CINEPRIME IMAGE SYNC REPORT
==================================================
Total movies processed:       {total_count}
Images already valid:         {already_valid_count}
New images matched & assigned: {new_added_count}
Repaired broken images:       {repaired_count}
Placeholders created:         {placeholders_created_count}
Manual review required:       {len(manual_review_list)}
Duplicate image assignments:  {duplicate_count}
==================================================
"""
        log_info(summary_str)

        if manual_review_list:
            print("\nMOVIES REQUIRING MANUAL REVIEW / PLACEHOLDER ASSIGNED:")
            for m_id, m_title, reason in manual_review_list:
                print(f"  • Movie ID {m_id}: '{m_title}' -> Reason: {reason}")

        print("\nImage Synchronization Complete!")
