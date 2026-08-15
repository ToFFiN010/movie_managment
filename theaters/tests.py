from django.test import TestCase
from theaters.models import Theater, Screen, Seat

class TheatersTestCase(TestCase):
    def setUp(self):
        self.theater = Theater.objects.create(
            name='CineMax',
            location='Downtown',
            address='100 Main St',
            city='New York'
        )

    def test_screen_creation_and_auto_seat_generation(self):
        screen = Screen.objects.create(
            theater=self.theater,
            screen_number=1,
            capacity=30,
            screen_type=Screen.ScreenType.IMAX
        )
        # Seats should be auto-generated upon creation
        seats_count = Seat.objects.filter(screen=screen).count()
        self.assertGreater(seats_count, 0)
        self.assertTrue(Seat.objects.filter(screen=screen, row='A', seat_number=1).exists())
