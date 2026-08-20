import os
from PIL import Image
from django.core.management.base import BaseCommand
from movies.models import Movie, MovieImage

class Command(BaseCommand):
    help = 'Validates file existence, MIME headers, corruption, and dimensions for all movie posters in DB.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Verifying movie poster file integrity..."))
        movies = Movie.objects.all()

        verified_count = 0
        corrupt_count = 0
        missing_count = 0

        for m in movies:
            if not m.poster:
                missing_count += 1
                self.stdout.write(self.style.WARNING(f"[-] ID {m.id}: '{m.title}' has no poster assigned."))
                continue

            try:
                path = m.poster.path
                if not os.path.exists(path):
                    missing_count += 1
                    self.stdout.write(self.style.ERROR(f"[!] ID {m.id}: '{m.title}' file does not exist: {path}"))
                    continue

                with Image.open(path) as img:
                    img.verify()

                with Image.open(path) as img:
                    w, h = img.size
                    fmt = img.format

                verified_count += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] ID {m.id}: '{m.title}' -> Verified {fmt} ({w}x{h}px)"))

            except Exception as e:
                corrupt_count += 1
                self.stdout.write(self.style.ERROR(f"[X] ID {m.id}: '{m.title}' -> Corrupted image file ({e})"))

        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"VERIFICATION RESULTS: Verified: {verified_count} | Missing: {missing_count} | Corrupt: {corrupt_count}"))
