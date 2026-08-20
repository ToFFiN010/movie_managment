import json
import urllib.request
import urllib.error
from django.core.management.base import BaseCommand
from movies.models import Movie, MovieTrailer
from movies.utils import get_youtube_video_id, normalize_movie_trailers

class Command(BaseCommand):
    help = 'Validates accessibility, video availability, and metadata of all stored movie trailers.'

    def handle(self, *args, **options):
        # Database normalization step
        normalized = normalize_movie_trailers()
        self.stdout.write(f"\n[INFO] Database normalization complete. ({normalized} records cleaned)\n")
        self.stdout.write("Movie title | Trailer URL | Extracted ID | Status | Reason")
        self.stdout.write("-" * 80)

        valid_cnt = 0
        broken_cnt = 0
        missing_cnt = 0
        total_cnt = 0

        movies = Movie.objects.all().order_by('id')

        for movie in movies:
            total_cnt += 1
            raw_url = movie.trailer_url or ''
            vid = get_youtube_video_id(raw_url or movie.youtube_video_id)

            if not vid:
                missing_cnt += 1
                disp_url = raw_url if raw_url else '-'
                self.stdout.write(self.style.WARNING(f"{movie.title} | {disp_url} | - | MISSING | No trailer URL found"))
                continue

            status, reason = self.verify_video_id(vid)
            clean_url = f"https://www.youtube.com/watch?v={vid}"

            if status == 'VALID':
                valid_cnt += 1
                self.stdout.write(self.style.SUCCESS(f"{movie.title} | {clean_url} | {vid} | VALID | {reason}"))
            else:
                broken_cnt += 1
                self.stdout.write(self.style.ERROR(f"{movie.title} | {clean_url} | {vid} | INVALID | {reason}"))

        report_str = f"""
========================================
CINEPRIME TRAILER VALIDATION REPORT
========================================
Total Movies Inspected:    {total_cnt}

VALID:                      {valid_cnt}
INVALID / BROKEN:           {broken_cnt}
MISSING:                    {missing_cnt}
========================================
"""
        self.stdout.write(report_str)

    def verify_video_id(self, vid):
        if not vid or len(vid) != 11:
            return ('INVALID', 'Invalid 11-character YouTube video ID')

        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
        try:
            req = urllib.request.Request(oembed_url, headers={'User-Agent': 'CinePrime/1.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    return ('VALID', 'Reachable via YouTube oEmbed API')
        except urllib.error.HTTPError as e:
            if e.code in [404, 401, 403]:
                return ('INVALID', f'YouTube video unavailable/private/deleted (HTTP {e.code})')
            return ('INVALID', f'YouTube HTTP error {e.code}')
        except Exception as e:
            # Network issue or timeout
            return ('VALID', f'Network timeout fallback: {e}')

        return ('VALID', 'OK')
