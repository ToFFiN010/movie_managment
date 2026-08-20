import os
from PIL import Image
from django.core.management.base import BaseCommand
from movies.models import Movie

class Command(BaseCommand):
    help = 'Inspects every movie and reports physical file existence, size, image format, and diagnostic status.'

    def handle(self, *args, **options):
        self.stdout.write("\n=========================================")
        self.stdout.write("CINEPRIME MOVIE IMAGE DIAGNOSTIC REPORT")
        self.stdout.write("=========================================\n")

        movies = Movie.objects.all().order_by('id')
        total = movies.count()

        ok_cnt = 0
        missing_db_cnt = 0
        missing_file_cnt = 0
        broken_cnt = 0
        empty_cnt = 0
        placeholder_cnt = 0

        for movie in movies:
            poster_field = movie.poster.name if movie.poster else ''
            poster_url = movie.get_poster_url
            file_exists = False
            file_size_kb = 0
            img_format = 'N/A'
            status = 'MISSING_DATABASE_IMAGE'
            reason = ''

            if movie.poster:
                try:
                    file_path = movie.poster.path
                    if os.path.exists(file_path):
                        file_exists = True
                        size_bytes = os.path.getsize(file_path)
                        file_size_kb = round(size_bytes / 1024.0, 1)

                        if size_bytes == 0:
                            status = 'EMPTY_IMAGE'
                            reason = '0 bytes file'
                            empty_cnt += 1
                        else:
                            try:
                                with Image.open(file_path) as img:
                                    img.verify()
                                    img_format = img.format or 'UNKNOWN'
                                    if getattr(movie, 'poster_source', None) == 'placeholder' or 'fallback' in poster_field:
                                        status = 'PLACEHOLDER_ONLY'
                                        placeholder_cnt += 1
                                    else:
                                        status = 'OK'
                                        ok_cnt += 1
                            except Exception as e:
                                status = 'BROKEN_IMAGE'
                                reason = f"PIL Verification Error: {e}"
                                broken_cnt += 1
                    else:
                        status = 'MISSING_PHYSICAL_FILE'
                        missing_file_cnt += 1
                except Exception as e:
                    status = 'BROKEN_IMAGE'
                    reason = str(e)
                    broken_cnt += 1
            else:
                if movie.poster_path or movie.tmdb_poster_url:
                    status = 'PLACEHOLDER_ONLY'
                    placeholder_cnt += 1
                else:
                    status = 'MISSING_DATABASE_IMAGE'
                    missing_db_cnt += 1

            self.stdout.write(f"#{movie.id} | {movie.title} ({movie.release_year})")
            self.stdout.write(f"   Poster Field: {poster_field or '[EMPTY]'}")
            self.stdout.write(f"   Poster URL:   {poster_url}")
            self.stdout.write(f"   File Exists:  {'YES' if file_exists else 'NO'} ({file_size_kb} KB, Format: {img_format})")
            
            if status == 'OK':
                self.stdout.write(self.style.SUCCESS(f"   Status:       {status}"))
            elif status == 'PLACEHOLDER_ONLY':
                self.stdout.write(self.style.WARNING(f"   Status:       {status}"))
            else:
                self.stdout.write(self.style.ERROR(f"   Status:       {status} {('(' + reason + ')') if reason else ''}"))
            self.stdout.write("-" * 60)

        summary_str = f"""
========================================
DIAGNOSTIC SUMMARY
========================================
Total Movies Inspected:     {total}

OK (Valid Local Poster):    {ok_cnt}
MISSING_DATABASE_IMAGE:     {missing_db_cnt}
MISSING_PHYSICAL_FILE:      {missing_file_cnt}
BROKEN_IMAGE / EMPTY:       {broken_cnt + empty_cnt}
PLACEHOLDER_ONLY:           {placeholder_cnt}
========================================
"""
        self.stdout.write(summary_str)
