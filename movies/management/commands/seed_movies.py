import os
from datetime import date, time, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie, Genre, Language
from theaters.models import Theater, Screen
from bookings.models import ShowSchedule


class Command(BaseCommand):
    help = 'Seeds the database with a balanced mixture of NOW SHOWING and UPCOMING movies.'

    def handle(self, *args, **options):
        self.stdout.write("Starting CinePrime Movie Database Seeding...")

        # 1. Ensure Languages
        lang_en, _ = Language.objects.get_or_create(code='en', defaults={'name': 'English'})
        lang_hi, _ = Language.objects.get_or_create(code='hi', defaults={'name': 'Hindi'})
        lang_ta, _ = Language.objects.get_or_create(code='ta', defaults={'name': 'Tamil'})
        lang_te, _ = Language.objects.get_or_create(code='te', defaults={'name': 'Telugu'})
        lang_kn, _ = Language.objects.get_or_create(code='kn', defaults={'name': 'Kannada'})

        # 2. Ensure Genres
        genres_data = [
            ('Action', 'action'),
            ('Adventure', 'adventure'),
            ('Sci-Fi', 'sci-fi'),
            ('Drama', 'drama'),
            ('Comedy', 'comedy'),
            ('Thriller', 'thriller'),
            ('Crime', 'crime'),
            ('Horror', 'horror'),
            ('Animation', 'animation'),
            ('Fantasy', 'fantasy'),
        ]
        genre_objs = {}
        for name, slug in genres_data:
            g, _ = Genre.objects.get_or_create(slug=slug, defaults={'name': name})
            genre_objs[slug] = g

        # 3. Seed NOW SHOWING Movies (Release date <= today)
        now_showing_movies = [
            {
                'title': 'Oppenheimer',
                'slug': 'oppenheimer',
                'description': 'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb.',
                'short_description': 'The story of J. Robert Oppenheimer and the Manhattan Project.',
                'release_date': date(2023, 7, 21),
                'duration_minutes': 180,
                'age_certification': Movie.AgeCertification.A_18,
                'language': lang_en,
                'director': 'Christopher Nolan',
                'average_rating': 8.9,
                'total_reviews': 1250,
                'views': 4500,
                'status': Movie.Status.NOW_SHOWING,
                'poster_path': '/media/movies/posters/oppenheimer.jpg',
                'genres': ['drama', 'action']
            },
            {
                'title': 'Dune: Part Two',
                'slug': 'dune-part-two',
                'description': 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.',
                'short_description': 'Paul Atreides unites with the Fremen for epic revenge.',
                'release_date': date(2024, 3, 1),
                'duration_minutes': 166,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'Denis Villeneuve',
                'average_rating': 8.8,
                'total_reviews': 980,
                'views': 3800,
                'status': Movie.Status.NOW_SHOWING,
                'poster_path': '/media/movies/posters/dune_part_two.jpg',
                'genres': ['sci-fi', 'adventure', 'action']
            },
            {
                'title': 'John Wick: Chapter 4',
                'slug': 'john-wick-chapter-4',
                'description': 'John Wick uncovers a path to defeating The High Table. But before he can earn his freedom, Wick must face off against a new enemy.',
                'short_description': 'John Wick uncovers a path to defeating The High Table.',
                'release_date': date(2023, 3, 24),
                'duration_minutes': 169,
                'age_certification': Movie.AgeCertification.A_18,
                'language': lang_en,
                'director': 'Chad Stahelski',
                'average_rating': 8.7,
                'total_reviews': 850,
                'views': 3100,
                'status': Movie.Status.NOW_SHOWING,
                'poster_path': '/media/movies/posters/john_wick_chapter_4.jpg',
                'genres': ['action', 'crime', 'thriller']
            },
            {
                'title': 'Top Gun: Maverick',
                'slug': 'top-gun-maverick',
                'description': 'After thirty years, Maverick is still pushing the envelope as a top naval aviator, but must confront ghosts of his past.',
                'short_description': 'Maverick leads Top Gun graduates on a specialized mission.',
                'release_date': date(2022, 5, 27),
                'duration_minutes': 130,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'Joseph Kosinski',
                'average_rating': 8.6,
                'total_reviews': 1100,
                'views': 4200,
                'status': Movie.Status.NOW_SHOWING,
                'poster_path': '/media/movies/posters/top_gun_maverick.jpg',
                'genres': ['action', 'drama']
            },
            {
                'title': 'Barbie',
                'slug': 'barbie',
                'description': 'Barbie and Ken are having the time of their lives in the colorful and seemingly perfect world of Barbie Land.',
                'short_description': 'Barbie and Ken explore the real world beyond Barbie Land.',
                'release_date': date(2023, 7, 21),
                'duration_minutes': 114,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'Greta Gerwig',
                'average_rating': 8.4,
                'total_reviews': 950,
                'views': 3900,
                'status': Movie.Status.NOW_SHOWING,
                'poster_path': '/media/movies/posters/barbie.jpg',
                'genres': ['comedy', 'adventure']
            },
            {
                'title': 'Jawan',
                'slug': 'jawan',
                'description': 'A high-octane action thriller which outlines the emotional journey of a man who is set to rectify the wrongs in the society.',
                'short_description': 'A high-octane action thriller of a man rectifying societal wrongs.',
                'release_date': date(2023, 9, 7),
                'duration_minutes': 169,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_hi,
                'director': 'Atlee',
                'average_rating': 8.5,
                'total_reviews': 1400,
                'views': 5100,
                'status': Movie.Status.NOW_SHOWING,
                'poster_path': '/media/movies/posters/jawan.jpg',
                'genres': ['action', 'thriller']
            },
            {
                'title': 'Kalki 2898 AD',
                'slug': 'kalki-2898-ad',
                'description': 'A modern avatar of Vishnu, a Hindu god, who is believed to have descended to earth to protect the world from evil forces.',
                'short_description': 'A futuristic post-apocalyptic saga inspired by mythology.',
                'release_date': date(2024, 6, 27),
                'duration_minutes': 180,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_te,
                'director': 'Nag Ashwin',
                'average_rating': 8.6,
                'total_reviews': 1600,
                'views': 5800,
                'status': Movie.Status.NOW_SHOWING,
                'poster_path': '/media/movies/posters/kalki_2898_ad.jpg',
                'genres': ['sci-fi', 'action', 'fantasy']
            },
            {
                'title': '12th Fail',
                'slug': '12th-fail',
                'description': 'The real-life story of IPS Officer Manoj Kumar Sharma and his journey overcoming extreme hardship.',
                'short_description': 'Inspiring true story of Manoj Kumar Sharma becoming an IPS officer.',
                'release_date': date(2023, 10, 27),
                'duration_minutes': 147,
                'age_certification': Movie.AgeCertification.U,
                'language': lang_hi,
                'director': 'Vidhu Vinod Chopra',
                'average_rating': 9.1,
                'total_reviews': 2100,
                'views': 6400,
                'status': Movie.Status.NOW_SHOWING,
                'poster_path': '/media/movies/posters/12th_fail.jpg',
                'genres': ['drama']
            }
        ]

        # 4. Seed UPCOMING Movies (Release date in future)
        upcoming_movies = [
            {
                'title': 'Avatar 3: Fire and Ash',
                'slug': 'avatar-3-fire-and-ash',
                'description': 'Jake Sully and Neytiri encounter the Ash People, a aggressive clan of Na\'vi living near volcanic regions on Pandora.',
                'short_description': 'Jake Sully encounters the fierce volcanic Ash People of Pandora.',
                'release_date': date(2026, 12, 18),
                'duration_minutes': 195,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'James Cameron',
                'average_rating': 9.3,
                'total_reviews': 0,
                'views': 8200,
                'status': Movie.Status.UPCOMING,
                'poster_path': '/media/movies/posters/avatar_3_fire_and_ash.jpg',
                'genres': ['sci-fi', 'action', 'adventure']
            },
            {
                'title': 'The Batman Part II',
                'slug': 'the-batman-part-ii',
                'description': 'Bruce Wayne faces new corruption and sinister masterminds threatening the foundation of Gotham City.',
                'short_description': 'Batman faces deep-rooted corruption and new threats in Gotham.',
                'release_date': date(2026, 10, 2),
                'duration_minutes': 175,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'Matt Reeves',
                'average_rating': 9.1,
                'total_reviews': 0,
                'views': 7400,
                'status': Movie.Status.UPCOMING,
                'poster_path': '/media/movies/posters/the_batman_part_ii.jpg',
                'genres': ['action', 'crime', 'thriller']
            },
            {
                'title': 'Spider-Man: Brand New Day',
                'slug': 'spider-man-brand-new-day',
                'description': 'Peter Parker navigates a new era of superhero challenges and unexpected allies across New York City.',
                'short_description': 'Peter Parker embarks on a brand new chapter as Spider-Man.',
                'release_date': date(2026, 7, 24),
                'duration_minutes': 150,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'Destin Daniel Cretton',
                'average_rating': 9.0,
                'total_reviews': 0,
                'views': 9100,
                'status': Movie.Status.UPCOMING,
                'poster_path': '/media/movies/posters/spider_man_brand_new_day.jpg',
                'genres': ['action', 'sci-fi', 'adventure']
            },
            {
                'title': 'Avengers: Doomsday 2026',
                'slug': 'avengers-doomsday-2026',
                'description': 'Earth\'s Mightiest Heroes assemble against Doctor Doom in a catastrophic multiversal battle for existence.',
                'short_description': 'The Avengers face Doctor Doom in a multiversal showdown.',
                'release_date': date(2026, 5, 1),
                'duration_minutes': 185,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'Anthony and Joe Russo',
                'average_rating': 9.5,
                'total_reviews': 0,
                'views': 12000,
                'status': Movie.Status.UPCOMING,
                'poster_path': '/media/movies/posters/avengers_doomsday_2026.jpg',
                'genres': ['action', 'sci-fi', 'adventure']
            },
            {
                'title': 'Salaar: Part 2 – Shouryaanga Parvam',
                'slug': 'salaar-part-2-shouryaanga-parvam',
                'description': 'The intense conflict deepens as Deva and Varadha navigate empire politics and fierce rivalry in Khansaar.',
                'short_description': 'Deva and Varadha\'s legendary conflict reaches explosive climaxes.',
                'release_date': date(2026, 9, 15),
                'duration_minutes': 180,
                'age_certification': Movie.AgeCertification.A_18,
                'language': lang_te,
                'director': 'Prashanth Neel',
                'average_rating': 8.9,
                'total_reviews': 0,
                'views': 6800,
                'status': Movie.Status.UPCOMING,
                'poster_path': '/media/movies/posters/salaar_part_2_shouryaanga_parvam.jpg',
                'genres': ['action', 'drama', 'thriller']
            },
            {
                'title': 'Kalki 2898 AD - Part 2',
                'slug': 'kalki-2898-ad-part-2',
                'description': 'Bhairava and Ashwatthama\'s battle escalates as the destiny of the newborn Kalki hangs in the balance.',
                'short_description': 'The epic continuation of Kalki 2898 AD\'s mythological sci-fi saga.',
                'release_date': date(2026, 11, 20),
                'duration_minutes': 185,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_te,
                'director': 'Nag Ashwin',
                'average_rating': 9.1,
                'total_reviews': 0,
                'views': 7600,
                'status': Movie.Status.UPCOMING,
                'poster_path': '/media/movies/posters/kalki_2898_ad_part_2.jpg',
                'genres': ['sci-fi', 'action', 'fantasy']
            },
            {
                'title': 'The Mandalorian & Grogu',
                'slug': 'the-mandalorian-grogu',
                'description': 'Din Djarin and Grogu embark on a grand cinematic adventure across outer rim Star Wars territories.',
                'short_description': 'Din Djarin and Grogu journey across outer rim galaxies.',
                'release_date': date(2026, 5, 22),
                'duration_minutes': 135,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'Jon Favreau',
                'average_rating': 8.7,
                'total_reviews': 0,
                'views': 5400,
                'status': Movie.Status.UPCOMING,
                'poster_path': '/media/movies/posters/the_mandalorian_grogu.jpg',
                'genres': ['sci-fi', 'adventure']
            },
            {
                'title': 'Supergirl: Woman of Tomorrow',
                'slug': 'supergirl-woman-of-tomorrow',
                'description': 'Kara Zor-El travels across alien worlds with Krypto to confront dark galactic forces.',
                'short_description': 'Kara Zor-El embarks on a cosmic journey across alien worlds.',
                'release_date': date(2026, 6, 26),
                'duration_minutes': 140,
                'age_certification': Movie.AgeCertification.UA,
                'language': lang_en,
                'director': 'Craig Gillespie',
                'average_rating': 8.6,
                'total_reviews': 0,
                'views': 4900,
                'status': Movie.Status.UPCOMING,
                'poster_path': '/media/movies/posters/supergirl_woman_of_tomorrow.jpg',
                'genres': ['action', 'sci-fi', 'adventure']
            }
        ]

        count_ns = 0
        count_up = 0

        all_seed_data = now_showing_movies + upcoming_movies

        for data in all_seed_data:
            genres_list = data.pop('genres')
            movie, created = Movie.objects.update_or_create(
                slug=data['slug'],
                defaults=data
            )
            for g_slug in genres_list:
                if g_slug in genre_objs:
                    movie.genres.add(genre_objs[g_slug])

            if movie.status == Movie.Status.NOW_SHOWING:
                count_ns += 1
            else:
                count_up += 1

        # 5. Ensure ShowSchedules exist for NOW_SHOWING movies
        theaters = list(Theater.objects.filter(status=Theater.Status.ACTIVE))
        if theaters:
            now_showing_qs = Movie.objects.filter(status=Movie.Status.NOW_SHOWING)
            today = date.today()
            for movie in now_showing_qs:
                for th in theaters[:2]:
                    screens = list(th.screens.all())
                    if screens:
                        screen = screens[0]
                        # Create showtime for today and tomorrow
                        for day_offset in range(0, 3):
                            s_date = today + timedelta(days=day_offset)
                            if not ShowSchedule.objects.filter(movie=movie, theater=th, screen=screen, show_date=s_date).exists():
                                try:
                                    ShowSchedule.objects.create(
                                        movie=movie,
                                        theater=th,
                                        screen=screen,
                                        show_date=s_date,
                                        start_time=time(18, 30),
                                        end_time=time(21, 30),
                                        ticket_price=Decimal('250.00'),
                                        status=ShowSchedule.Status.OPEN
                                    )
                                except Exception:
                                    pass

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded movies database!\n"
                f"- NOW SHOWING movies: {count_ns}\n"
                f"- UPCOMING movies: {count_up}\n"
                f"- Total movies seeded/updated: {len(all_seed_data)}"
            )
        )
