import os
import hashlib
from collections import defaultdict
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie

class Command(BaseCommand):
    help = 'Audits every Movie record in the database for poster and backdrop image integrity.'

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        movies = Movie.objects.all().order_by('id')

        total_movies = movies.count()
        valid_posters = 0
        missing_posters = 0
        broken_paths = 0
        invalid_formats = 0
        hash_map = defaultdict(list)

        header_fmt = "{:<4} | {:<32} | {:<36} | {:<11} | {:<7} | {:<6} | {:<9} | {:<10}"
        row_fmt = "{:<4} | {:<32} | {:<36} | {:<11} | {:<7} | {:<6} | {:<9} | {:<10}"

        self.stdout.write("=" * 135)
        self.stdout.write(self.style.MIGRATE_HEADING("CINEPRIME MOVIE POSTER & IMAGE SYSTEM DIAGNOSTIC AUDIT"))
        self.stdout.write("=" * 135)
        self.stdout.write(header_fmt.format(
            "ID", "Title", "Poster Path Value", "File Exists", "Valid", "Format", "Dimensions", "Size (KB)"
        ))
        self.stdout.write("-" * 135)

        for movie in movies:
            poster = movie.poster
            title_display = (movie.title[:30] + '..') if len(movie.title) > 32 else movie.title
            
            if not poster or not poster.name:
                missing_posters += 1
                self.stdout.write(row_fmt.format(
                    movie.id, title_display, "NONE / NULL", "NO", "NO", "-", "-", "0"
                ))
                continue

            rel_path = poster.name
            abs_path = media_root / rel_path

            if not abs_path.exists():
                missing_posters += 1
                broken_paths += 1
                self.stdout.write(row_fmt.format(
                    movie.id, title_display, rel_path[:35], "NO", "NO", "-", "-", "0"
                ))
                continue

            file_size_bytes = abs_path.stat().st_size
            file_size_kb = round(file_size_bytes / 1024, 1)

            if file_size_bytes == 0:
                broken_paths += 1
                self.stdout.write(row_fmt.format(
                    movie.id, title_display, rel_path[:35], "YES (0B)", "NO", "EMPTY", "0x0", "0"
                ))
                continue

            try:
                with open(abs_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                hash_map[file_hash].append((movie.id, movie.title))

                with Image.open(abs_path) as im:
                    fmt = im.format or "UNKNOWN"
                    w, h = im.size
                    im.verify()

                if fmt not in ['JPEG', 'PNG', 'WEBP']:
                    invalid_formats += 1

                valid_posters += 1
                self.stdout.write(row_fmt.format(
                    movie.id, title_display, rel_path[:35], "YES", "YES", fmt, f"{w}x{h}", str(file_size_kb)
                ))

            except Exception as e:
                broken_paths += 1
                self.stdout.write(row_fmt.format(
                    movie.id, title_display, rel_path[:35], "YES", "CORRUPT", "CORRUPT", "-", str(file_size_kb)
                ))

        # Check duplicate image assignments
        duplicate_assignments = 0
        duplicate_details = []
        for file_hash, assigned_movies in hash_map.items():
            if len(assigned_movies) > 1:
                duplicate_assignments += len(assigned_movies)
                duplicate_details.append(assigned_movies)

        self.stdout.write("=" * 135)
        self.stdout.write(self.style.SUCCESS("DIAGNOSTIC AUDIT SUMMARY"))
        self.stdout.write("=" * 135)
        self.stdout.write(f"Total movies in database:      {total_movies}")
        self.stdout.write(f"Movies with valid posters:     {valid_posters}")
        self.stdout.write(f"Movies missing posters:       {missing_posters}")
        self.stdout.write(f"Broken image paths / files:   {broken_paths}")
        self.stdout.write(f"Invalid image formats:        {invalid_formats}")
        self.stdout.write(f"Duplicate image assignments:  {duplicate_assignments}")

        if duplicate_details:
            self.stdout.write("\nDuplicate Poster Assignments Detected:")
            for dup_list in duplicate_details:
                titles = ", ".join([f"{m_id}: {m_title}" for m_id, m_title in dup_list])
                self.stdout.write(f"  • Same image file assigned to: {titles}")

        self.stdout.write("=" * 135 + "\n")
