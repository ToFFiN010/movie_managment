from django.core.management.base import BaseCommand
from bookings.services import release_expired_bookings, release_expired_reservations_for_show

class Command(BaseCommand):
    help = 'Releases all expired seat reservations and cancels stale pending bookings.'

    def handle(self, *args, **options):
        expired_reservations = release_expired_reservations_for_show()
        expired_bookings = release_expired_bookings()

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired Seat Release Complete: {expired_reservations} active reservations expired, {expired_bookings} pending bookings released."
            )
        )
