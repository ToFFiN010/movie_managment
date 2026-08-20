from django.core.management.base import BaseCommand
from movies.models import Movie
from movies.services.youtube_trailer import search_youtube_trailers, score_trailer_candidate, extract_youtube_id

class Command(BaseCommand):
    help = 'Searches YouTube and repairs official trailers for all database movies.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force re-repair of existing trailers.')

    def handle(self, *args, **options):
        force = options.get('force', False)
        self.stdout.write("\nStarting CinePrime Movie Trailer Repair Pipeline...\n")

        movies = Movie.objects.all().order_by('id')
        total = movies.count()

        repaired_cnt = 0
        existing_cnt = 0
        failed_cnt = 0

        for idx, movie in enumerate(movies, start=1):
            title = movie.title.strip()
            year = movie.release_year

            if not force and movie.youtube_video_id and len(movie.youtube_video_id) == 11 and movie.trailer_verified:
                existing_cnt += 1
                self.stdout.write(self.style.SUCCESS(f"[{idx}/{total}] [SKIP] #{movie.id} '{title}' trailer already verified."))
                continue

            candidates = search_youtube_trailers(title, release_year=year, director=movie.director)
            best_candidate = None
            best_score = -1
            best_decision = 'REJECT'
            best_type = 'OFFICIAL_TRAILER'

            for candidate in candidates:
                score, decision, reason, t_type = score_trailer_candidate(candidate, movie)
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
                    best_decision = decision
                    best_type = t_type

            if best_candidate and best_score >= 70 and best_decision != 'REJECT':
                vid = extract_youtube_id(best_candidate.get('video_id') or best_candidate.get('trailer_url'))
                if vid and len(vid) == 11:
                    movie.youtube_video_id = vid
                    movie.trailer_url = f"https://www.youtube.com/watch?v={vid}"
                    movie.trailer_title = best_candidate.get('video_title') or f"{title} Official Trailer"
                    movie.trailer_source = "YouTube"
                    movie.trailer_type = best_type
                    movie.trailer_verified = True
                    movie.save()

                    repaired_cnt += 1
                    self.stdout.write(self.style.SUCCESS(f"[{idx}/{total}] [OK] #{movie.id} '{title}' -> Trailer ID: {vid} (Score: {best_score}%)"))
                else:
                    failed_cnt += 1
                    self.stdout.write(self.style.ERROR(f"[{idx}/{total}] [FAIL] #{movie.id} '{title}' -> Invalid candidate ID"))
            else:
                failed_cnt += 1
                self.stdout.write(self.style.WARNING(f"[{idx}/{total}] [WARN] #{movie.id} '{title}' -> No confident candidate found"))

        summary_str = f"""
========================================
TRAILER REPAIR SUMMARY REPORT
========================================
Total Movies Processed:    {total}

Trailers Repaired/Assigned:{repaired_cnt}
Already Valid Trailers:    {existing_cnt}
Failed / Manual Review:    {failed_cnt}
========================================
"""
        self.stdout.write(summary_str)
