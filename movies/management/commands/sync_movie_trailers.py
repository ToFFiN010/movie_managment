import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from movies.models import Movie, MovieTrailer
from movies.services.youtube_trailer import (
    search_youtube_trailers,
    score_trailer_candidate,
    extract_youtube_id
)

# Set up logging to logs/movie_trailers.log
LOG_DIR = settings.BASE_DIR / 'logs'
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = LOG_DIR / 'movie_trailers.log'

logger = logging.getLogger('movie_trailers_sync')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
if not logger.handlers:
    logger.addHandler(file_handler)

def log_info(msg):
    logger.info(msg)

def log_warning(msg):
    logger.warning(msg)

def log_error(msg):
    logger.error(msg)


class Command(BaseCommand):
    help = 'Idempotently synchronizes official movie trailers from YouTube with confidence scoring and manual review safeguards.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Perform search and candidate scoring without modifying database')
        parser.add_argument('--force', action='store_true', help='Re-evaluate existing verified trailers')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(f"\n{prefix}Starting CinePrime Official Movie Trailer Sync Pipeline...\n")
        log_info(f"{prefix}Starting CinePrime Official Movie Trailer Sync Pipeline (DryRun={dry_run}, Force={force})")

        total_movies = 0
        existing_valid = 0
        new_added = 0
        no_trailer_found = 0
        manual_review_cnt = 0
        broken_cnt = 0
        rejected_cnt = 0

        manual_review_list = []

        movies = Movie.objects.all().order_by('id')

        for movie in movies:
            total_movies += 1
            has_verified = movie.trailers.filter(is_primary=True, verification_status='VERIFIED').exists()

            if has_verified and not force:
                existing_valid += 1
                curr_tr = movie.primary_trailer
                msg = f"SKIP (Already Verified): #{movie.id} '{movie.title}' -> Video ID: {curr_tr.video_id} ({curr_tr.channel_name})"
                self.stdout.write(self.style.SUCCESS(f"[OK] {msg}"))
                log_info(msg)
                continue

            # Search YouTube for candidate trailers
            candidates = search_youtube_trailers(movie.title, movie.release_year, movie.director)

            if not candidates:
                no_trailer_found += 1
                msg = f"NO TRAILER FOUND: #{movie.id} '{movie.title}'"
                self.stdout.write(self.style.WARNING(f"[WARN] {msg}"))
                log_warning(msg)

                if not dry_run:
                    MovieTrailer.objects.get_or_create(
                        movie=movie,
                        trailer_url="",
                        video_id="NO_TRAILER",
                        defaults={
                            'video_title': 'No Official Trailer Found',
                            'verification_status': MovieTrailer.VerificationStatus.NO_TRAILER_FOUND,
                            'notes_or_reason': 'Automated search yielded no candidates',
                        }
                    )
                continue

            # Evaluate candidate scores
            best_candidate = None
            best_score = -1
            best_decision = 'REJECT'
            best_reason = ''
            best_type = 'OFFICIAL_TRAILER'

            for candidate in candidates:
                score, decision, reason, t_type = score_trailer_candidate(candidate, movie)
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
                    best_decision = decision
                    best_reason = reason
                    best_type = t_type

            if not best_candidate or best_decision == 'REJECT':
                rejected_cnt += 1
                msg = f"REJECTED ALL CANDIDATES: #{movie.id} '{movie.title}' (Best score: {best_score} - {best_reason})"
                self.stdout.write(self.style.ERROR(f"[FAIL] {msg}"))
                log_warning(msg)
                continue

            vid = best_candidate['video_id']
            ch_name = best_candidate['channel_name']
            v_title = best_candidate['video_title']
            yt_url = f"https://www.youtube.com/watch?v={vid}"

            if best_decision == 'AUTO_APPROVE':
                new_added += 1
                msg = f"AUTO APPROVE ({best_score}%): #{movie.id} '{movie.title}' -> '{v_title}' [{ch_name}]"
                self.stdout.write(self.style.SUCCESS(f"[OK] {msg}"))
                log_info(msg)

                if not dry_run:
                    with transaction.atomic():
                        trailer, created = MovieTrailer.objects.update_or_create(
                            movie=movie,
                            video_id=vid,
                            defaults={
                                'trailer_url': yt_url,
                                'video_title': v_title,
                                'channel_name': ch_name,
                                'trailer_type': best_type,
                                'is_primary': True,
                                'confidence_score': best_score,
                                'verification_status': MovieTrailer.VerificationStatus.VERIFIED,
                                'verification_date': timezone.now(),
                                'thumbnail_url': best_candidate.get('thumbnail_url'),
                                'notes_or_reason': best_reason,
                            }
                        )

            elif best_decision == 'MANUAL_REVIEW':
                manual_review_cnt += 1
                msg = f"MANUAL REVIEW ({best_score}%): #{movie.id} '{movie.title}' -> '{v_title}' [{ch_name}]"
                self.stdout.write(self.style.WARNING(f"[WARN] {msg}"))
                log_warning(msg)

                manual_review_list.append({
                    'id': movie.id,
                    'title': movie.title,
                    'candidate_title': v_title,
                    'url': yt_url,
                    'channel': ch_name,
                    'score': best_score,
                    'reason': best_reason,
                })

                if not dry_run:
                    with transaction.atomic():
                        MovieTrailer.objects.get_or_create(
                            movie=movie,
                            video_id=vid,
                            defaults={
                                'trailer_url': yt_url,
                                'video_title': v_title,
                                'channel_name': ch_name,
                                'trailer_type': best_type,
                                'is_primary': False,
                                'confidence_score': best_score,
                                'verification_status': MovieTrailer.VerificationStatus.MANUAL_REVIEW_REQUIRED,
                                'thumbnail_url': best_candidate.get('thumbnail_url'),
                                'notes_or_reason': f"Confidence {best_score}%: {best_reason}",
                            }
                        )

        # Print Final Report
        report_str = f"""
========================================
CINEPRIME TRAILER SYNC {prefix}REPORT
========================================

Total Movies:              {total_movies}

Existing Valid Trailers:    {existing_valid}
New Trailers Added:        {new_added}
No Trailer Found:          {no_trailer_found}
Manual Review Required:    {manual_review_cnt}
Broken Trailers:           {broken_cnt}
Rejected Mismatches:       {rejected_cnt}

========================================
"""
        self.stdout.write(report_str)
        log_info(report_str)

        if manual_review_list:
            self.stdout.write("\nMOVIES REQUIRING MANUAL REVIEW:")
            for item in manual_review_list:
                self.stdout.write(f"  • #{item['id']} '{item['title']}':")
                self.stdout.write(f"      Candidate:  {item['candidate_title']}")
                self.stdout.write(f"      YouTube:    {item['url']}")
                self.stdout.write(f"      Channel:    {item['channel']}")
                self.stdout.write(f"      Score:      {item['score']}% ({item['reason']})")
                self.stdout.write(f"      Action:     Review in Admin at /admin/movie-trailers/\n")

        self.stdout.write(self.style.SUCCESS(f"{prefix}Trailer Sync Complete!\n"))
