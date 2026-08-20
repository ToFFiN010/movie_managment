from django.core.management.base import BaseCommand
from movies.services.image_recovery_service import MovieImageAuditService

class Command(BaseCommand):
    help = 'Fetches missing/unverified movie posters or generates CinePrime branded placeholders.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run audit and simulation without modifying files or database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        mode_str = " (DRY-RUN MODE)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"Starting Movie Poster Recovery Pipeline{mode_str}..."))

        summary, report = MovieImageAuditService.fetch_and_recover_posters(dry_run=dry_run)

        self.stdout.write("\n" + "="*80)
        self.stdout.write("MOVIE IMAGE IMPORT REPORT")
        self.stdout.write("="*80)
        self.stdout.write(f"Total movies processed:        {summary['total']}")
        self.stdout.write(f"Already valid images:          {summary['already_valid']}")
        self.stdout.write(f"Images successfully added:     {summary['added']}")
        self.stdout.write(f"Images replaced:               {summary['replaced']}")
        self.stdout.write(f"Placeholders created:          {summary['placeholders_created']}")
        self.stdout.write(f"Broken images fixed:           {summary['broken_fixed']}")
        self.stdout.write(f"Duplicate images detected:     {summary['duplicates_detected']}")
        self.stdout.write(f"Manual review required:        {summary['manual_review_required']}")
        self.stdout.write(f"Copyright review required:    {summary['copyright_review_required']}")
        self.stdout.write(f"Failed downloads:              {summary['failed']}")
        self.stdout.write("="*80 + "\n")
