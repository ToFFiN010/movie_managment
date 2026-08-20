import os
import urllib.request
import urllib.parse
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie

class Command(BaseCommand):
    help = 'Audits every movie record and produces status reports: OK, MISSING, BROKEN, INVALID, PLACEHOLDER, NEEDS_REVIEW.'

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        movies = Movie.objects.all().order_by('id')
        total = movies.count()

        counts = {
            'OK': 0,
            'MISSING': 0,
            'BROKEN': 0,
            'INVALID': 0,
            'PLACEHOLDER': 0,
            'NEEDS_REVIEW': 0,
        }

        self.stdout.write("================================================================================")
        self.stdout.write("                    CINEPRIME MOVIE IMAGE AUDIT REPORT                         ")
        self.stdout.write("================================================================================\n")

        for movie in movies:
            poster_field = movie.poster.name if movie.poster else None
            poster_url = movie.get_poster_url
            poster_source = getattr(movie, 'poster_source', '')
            status = 'NEEDS_REVIEW'
            ref_exists = False
            url_valid = False
            img_format = 'N/A'
            img_dims = 'N/A'
            loading_status = 'Unknown'

            # 1. Determine status
            if not poster_field and not movie.poster_path and not movie.tmdb_poster_url and not movie.poster_source_url:
                status = 'MISSING'
                loading_status = 'No poster field or URL configured'
            elif poster_source == 'placeholder' or (poster_field and poster_field.endswith('_fallback.jpg')) or 'cineprime_default_fallback.png' in poster_url:
                status = 'PLACEHOLDER'
                loading_status = 'Displaying generated fallback placeholder'
                if poster_field:
                    abs_p = media_root / poster_field
                    if abs_p.exists():
                        ref_exists = True
                        try:
                            with Image.open(abs_p) as im:
                                img_format = im.format
                                img_dims = f"{im.size[0]}x{im.size[1]}"
                        except Exception:
                            pass
            elif poster_field:
                abs_p = media_root / poster_field
                if not abs_p.exists():
                    status = 'MISSING'
                    loading_status = f'File not found: {poster_field}'
                elif abs_p.stat().st_size == 0:
                    status = 'BROKEN'
                    loading_status = '0-byte empty file'
                    ref_exists = True
                else:
                    ref_exists = True
                    try:
                        with Image.open(abs_p) as im:
                            img_format = im.format
                            img_dims = f"{im.size[0]}x{im.size[1]}"
                            url_valid = True
                            if im.format not in ['JPEG', 'PNG', 'WEBP']:
                                status = 'INVALID'
                                loading_status = f'Unsupported format: {im.format}'
                            else:
                                status = 'OK'
                                loading_status = 'Valid local image'
                    except Exception as e:
                        status = 'BROKEN'
                        loading_status = f'Corrupt image file ({e})'
            elif poster_url and (poster_url.startswith('http://') or poster_url.startswith('https://')):
                # Check external URL validity
                try:
                    req = urllib.request.Request(poster_url, headers={'User-Agent': 'CinePrime/1.0'}, method='HEAD')
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        if resp.status == 200:
                            url_valid = True
                            status = 'OK'
                            loading_status = f'Valid external URL (HTTP 200)'
                        else:
                            status = 'BROKEN'
                            loading_status = f'External URL HTTP {resp.status}'
                except Exception as e:
                    # Retry GET if HEAD fails
                    try:
                        req = urllib.request.Request(poster_url, headers={'User-Agent': 'CinePrime/1.0'})
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            if resp.status == 200:
                                url_valid = True
                                status = 'OK'
                                loading_status = f'Valid external URL (HTTP 200)'
                            else:
                                status = 'BROKEN'
                                loading_status = f'External URL HTTP {resp.status}'
                    except Exception as ex:
                        status = 'BROKEN'
                        loading_status = f'Failed external fetch ({ex})'
            else:
                # Check if cached poster candidate exists on disk
                slug = movie.slug or f"movie-{movie.id}"
                cand = f"movies/posters/movie_{movie.id}_poster.webp"
                cand_abs = media_root / cand
                if cand_abs.exists() and cand_abs.stat().st_size > 1000:
                    ref_exists = True
                    url_valid = True
                    try:
                        with Image.open(cand_abs) as im:
                            img_format = im.format
                            img_dims = f"{im.size[0]}x{im.size[1]}"
                            status = 'OK'
                            loading_status = f'Found cached poster: {cand}'
                    except Exception:
                        status = 'BROKEN'
                        loading_status = 'Corrupt cached poster file'
                else:
                    status = 'NEEDS_REVIEW'
                    loading_status = 'Unverified poster path'

            counts[status] += 1

            color_style = self.style.SUCCESS if status == 'OK' else (
                self.style.WARNING if status in ['PLACEHOLDER', 'NEEDS_REVIEW'] else self.style.ERROR
            )

            self.stdout.write(color_style(f"[{status:<12}] Movie #{movie.id:2d}: '{movie.title}' ({movie.release_year})"))
            self.stdout.write(f"               Poster Field:  {poster_field or 'None'}")
            self.stdout.write(f"               Poster URL:    {poster_url}")
            self.stdout.write(f"               File Exists:   {ref_exists} | URL Valid: {url_valid}")
            self.stdout.write(f"               Format:        {img_format} | Dims: {img_dims}")
            self.stdout.write(f"               Status Note:   {loading_status}\n")

        self.stdout.write("================================================================================")
        self.stdout.write(f"AUDIT SUMMARY (Total Movies: {total})")
        self.stdout.write(f"  OK           : {counts['OK']}")
        self.stdout.write(f"  MISSING      : {counts['MISSING']}")
        self.stdout.write(f"  BROKEN       : {counts['BROKEN']}")
        self.stdout.write(f"  INVALID      : {counts['INVALID']}")
        self.stdout.write(f"  PLACEHOLDER  : {counts['PLACEHOLDER']}")
        self.stdout.write(f"  NEEDS_REVIEW : {counts['NEEDS_REVIEW']}")
        self.stdout.write("================================================================================\n")
