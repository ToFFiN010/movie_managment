import os
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie
from movies.utils import get_youtube_video_id

class Command(BaseCommand):
    help = 'Audits all movie posters, backdrop images, and official trailers across the database.'

    def handle(self, *args, **options):
        self.stdout.write("\n=========================================")
        self.stdout.write("CINEPRIME MOVIE MEDIA & TRAILER AUDIT")
        self.stdout.write("=========================================\n")

        movies = Movie.objects.all().order_by('id')
        total = movies.count()

        with_poster = 0
        without_poster = 0
        with_trailer = 0
        without_trailer = 0
        broken_image = 0
        invalid_trailer = 0
        placeholder_image = 0

        problematic_movies = []

        for movie in movies:
            title = movie.title
            year = movie.release_year
            
            # Poster check
            poster_status = 'PRESENT'
            poster_reason = 'OK'

            if movie.poster:
                try:
                    file_path = movie.poster.path
                    if not os.path.exists(file_path):
                        poster_status = 'BROKEN_URL'
                        poster_reason = 'Local poster file does not exist on disk'
                        broken_image += 1
                    elif os.path.getsize(file_path) == 0:
                        poster_status = 'EMPTY_FILE'
                        poster_reason = 'Poster file size is 0 bytes'
                        broken_image += 1
                    elif getattr(movie, 'poster_source', '') == 'placeholder' or 'fallback' in movie.poster.name:
                        poster_status = 'PLACEHOLDER'
                        poster_reason = 'CinePrime fallback placeholder'
                        placeholder_image += 1
                        with_poster += 1
                    else:
                        with_poster += 1
                except Exception as e:
                    poster_status = 'BROKEN_URL'
                    poster_reason = str(e)
                    broken_image += 1
            elif movie.poster_path or movie.tmdb_poster_url:
                poster_status = 'TMDB_URL_ONLY'
                poster_reason = 'Remote TMDb poster URL stored without local file'
                with_poster += 1
            else:
                poster_status = 'MISSING'
                poster_reason = 'Poster URL/field is empty'
                without_poster += 1

            # Trailer check
            trailer_status = 'PRESENT'
            trailer_reason = 'OK'
            vid = get_youtube_video_id(movie.trailer_url or movie.youtube_video_id)

            if vid and len(vid) == 11:
                with_trailer += 1
            elif movie.trailer_url or movie.youtube_video_id:
                trailer_status = 'INVALID'
                trailer_reason = 'Invalid or non-11-character YouTube video ID'
                invalid_trailer += 1
            else:
                trailer_status = 'MISSING'
                trailer_reason = 'No trailer URL or video ID assigned'
                without_trailer += 1

            if poster_status in ['MISSING', 'BROKEN_URL', 'EMPTY_FILE', 'PLACEHOLDER'] or trailer_status in ['MISSING', 'INVALID']:
                problematic_movies.append({
                    'id': movie.id,
                    'title': title,
                    'year': year,
                    'poster_status': poster_status,
                    'trailer_status': trailer_status,
                    'reason': f"Poster: {poster_reason} | Trailer: {trailer_reason}"
                })

        # Display Problematic Movies List
        self.stdout.write("PROBLEMATIC MOVIE DETAILS:")
        self.stdout.write("-" * 80)
        if problematic_movies:
            for item in problematic_movies:
                msg = f"[{item['id']}] {item['title']} ({item['year']}) | Poster: {item['poster_status']} | Trailer: {item['trailer_status']} | Reason: {item['reason']}"
                if item['poster_status'] == 'MISSING' or item['trailer_status'] == 'MISSING':
                    self.stdout.write(self.style.WARNING(msg))
                else:
                    self.stdout.write(self.style.ERROR(msg))
        else:
            self.stdout.write(self.style.SUCCESS("All movies have valid posters and official trailers!"))

        summary_str = f"""
========================================
AUDIT SUMMARY METRICS
========================================
TOTAL MOVIES:                  {total}
MOVIES WITH POSTER:            {with_poster}
MOVIES WITHOUT POSTER:         {without_poster}
MOVIES WITH TRAILER:           {with_trailer}
MOVIES WITHOUT TRAILER:        {without_trailer}
MOVIES WITH BROKEN IMAGE URL:  {broken_image}
MOVIES WITH INVALID TRAILER:   {invalid_trailer}
MOVIES WITH PLACEHOLDER IMAGE: {placeholder_image}
========================================
"""
        self.stdout.write(summary_str)
