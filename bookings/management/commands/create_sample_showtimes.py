from datetime import date, time, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from movies.models import Movie
from theaters.models import Theater, Screen
from bookings.models import ShowSchedule

class Command(BaseCommand):
    help = 'Populates safe sample showtimes for movies across active theaters and screens without time overlap conflicts.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Generating safe sample showtimes for CinePrime..."))

        movies = list(Movie.objects.filter(status__in=[Movie.Status.NOW_SHOWING, Movie.Status.UPCOMING]))
        if not movies:
            movies = list(Movie.objects.all()[:10])

        theaters = list(Theater.objects.prefetch_related('screens').all())
        if not theaters:
            self.stdout.write(self.style.ERROR("No theaters found in database."))
            return

        time_slots = [
            (time(10, 0), time(13, 0), Decimal('180.00')),
            (time(13, 30), time(16, 30), Decimal('200.00')),
            (time(17, 0), time(20, 0), Decimal('250.00')),
            (time(20, 30), time(23, 30), Decimal('220.00')),
        ]

        today = date.today()
        created_count = 0
        skipped_count = 0

        for day_offset in range(0, 5):
            target_date = today + timedelta(days=day_offset)
            m_idx = day_offset % len(movies) if movies else 0

            for t in theaters:
                screens = list(t.screens.all())
                for s_idx, screen in enumerate(screens):
                    current_movie = movies[(m_idx + s_idx) % len(movies)]

                    for slot_start, slot_end, base_price in time_slots:
                        # Check overlap conflict
                        exists = ShowSchedule.objects.filter(
                            screen=screen,
                            show_date=target_date,
                            status__in=[ShowSchedule.Status.UPCOMING, ShowSchedule.Status.OPEN],
                            start_time__lt=slot_end,
                            end_time__gt=slot_start
                        ).exists()

                        if exists:
                            skipped_count += 1
                            continue

                        # Price calculation based on screen type
                        price = base_price
                        if screen.screen_type in [Screen.ScreenType.IMAX, Screen.ScreenType.FOUR_DX]:
                            price = base_price + Decimal('100.00')
                        elif screen.screen_type == Screen.ScreenType.THREE_D:
                            price = base_price + Decimal('50.00')

                        show = ShowSchedule.objects.create(
                            movie=current_movie,
                            theater=t,
                            screen=screen,
                            show_date=target_date,
                            start_time=slot_start,
                            end_time=slot_end,
                            ticket_price=price,
                            status=ShowSchedule.Status.OPEN if target_date <= today + timedelta(days=3) else ShowSchedule.Status.UPCOMING
                        )
                        created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully generated {created_count} showtimes across {len(theaters)} theaters! (Skipped {skipped_count} overlapping slots)"))
