from datetime import date, time, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from accounts.models import User, UserProfile
from movies.models import Genre, Language, CastMember, Movie, MovieCast
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, Booking, BookingSeat, Payment
from reviews.models import Review

class Command(BaseCommand):
    help = "Seeds database with initial sample data for movies, theaters, screens, schedules, users, and reviews."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting database seeding process..."))

        # 1. Superuser / Admin & Demo User Creation
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@cineprime.com',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            UserProfile.objects.get_or_create(user=admin_user, defaults={'phone': '1234567890'})
            self.stdout.write("Created Admin user: admin / admin123")

        demo_user, created = User.objects.get_or_create(
            username='johndoe',
            defaults={
                'email': 'john@example.com',
                'role': User.Role.USER
            }
        )
        if created:
            demo_user.set_password('user123')
            demo_user.save()
            UserProfile.objects.get_or_create(user=demo_user, defaults={'phone': '9876543210'})
            self.stdout.write("Created Demo user: johndoe / user123")

        # 2. Languages
        languages_data = [
            ('English', 'en'),
            ('Tamil', 'ta'),
            ('Hindi', 'hi'),
            ('Telugu', 'te'),
            ('Malayalam', 'ml'),
            ('Kannada', 'kn'),
        ]
        lang_objs = {}
        for name, code in languages_data:
            obj, _ = Language.objects.get_or_create(name=name, defaults={'code': code})
            lang_objs[name] = obj

        # 3. Genres
        genres_data = [
            'Action', 'Adventure', 'Comedy', 'Drama', 'Horror',
            'Thriller', 'Romance', 'Sci-Fi', 'Fantasy', 'Animation',
            'Crime', 'Mystery'
        ]
        genre_objs = {}
        for name in genres_data:
            obj, _ = Genre.objects.get_or_create(name=name, defaults={'description': f'{name} movie genre'})
            genre_objs[name] = obj

        # 4. Cast Members
        cast_names = [
            'Christopher Nolan', 'Cillian Murphy', 'Robert Downey Jr.', 'Emily Blunt',
            'Denis Villeneuve', 'Timothée Chalamet', 'Zendaya', 'Florence Pugh',
            'Keanu Reeves', 'Chad Stahelski', 'Tom Cruise', 'Joseph Kosinski',
            'Margot Robbie', 'Ryan Gosling', 'Greta Gerwig', 'Leonardo DiCaprio',
            'Brad Pitt', 'Quentin Tarantino', 'Scarlett Johansson', 'Christian Bale'
        ]
        cast_objs = {}
        for name in cast_names:
            obj, _ = CastMember.objects.get_or_create(name=name, defaults={'biography': f'Renowned film personality {name}.'})
            cast_objs[name] = obj

        # 5. Movies
        movies_data = [
            {
                'title': 'Oppenheimer',
                'description': 'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb.',
                'short_description': 'The story of J. Robert Oppenheimer and the Manhattan Project.',
                'release_date': date(2023, 7, 21),
                'duration_minutes': 180,
                'age_certification': '16+',
                'language': lang_objs['English'],
                'director': 'Christopher Nolan',
                'trailer_url': 'https://www.youtube.com/watch?v=uYPbbksJxIg',
                'status': Movie.Status.NOW_SHOWING,
                'genres': [genre_objs['Drama'], genre_objs['Thriller']],
                'cast': [('Cillian Murphy', 'J. Robert Oppenheimer', 'Actor'), ('Robert Downey Jr.', 'Lewis Strauss', 'Actor'), ('Emily Blunt', 'Katherine Oppenheimer', 'Actress')]
            },
            {
                'title': 'Dune: Part Two',
                'description': 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.',
                'short_description': 'Paul Atreides unites with the Fremen on Arrakis.',
                'release_date': date(2024, 3, 1),
                'duration_minutes': 166,
                'age_certification': '13+',
                'language': lang_objs['English'],
                'director': 'Denis Villeneuve',
                'trailer_url': 'https://www.youtube.com/watch?v=Way9Dexny3w',
                'status': Movie.Status.NOW_SHOWING,
                'genres': [genre_objs['Sci-Fi'], genre_objs['Adventure']],
                'cast': [('Timothée Chalamet', 'Paul Atreides', 'Actor'), ('Zendaya', 'Chani', 'Actress'), ('Florence Pugh', 'Princess Irulan', 'Actress')]
            },
            {
                'title': 'John Wick: Chapter 4',
                'description': 'John Wick uncovers a path to defeating the High Table, but before he can earn his freedom, he must face off against a new enemy.',
                'short_description': 'John Wick faces his deadliest adversaries yet.',
                'release_date': date(2023, 3, 24),
                'duration_minutes': 169,
                'age_certification': '18+',
                'language': lang_objs['English'],
                'director': 'Chad Stahelski',
                'trailer_url': 'https://www.youtube.com/watch?v=qEVUtrk8_B4',
                'status': Movie.Status.NOW_SHOWING,
                'genres': [genre_objs['Action'], genre_objs['Crime']],
                'cast': [('Keanu Reeves', 'John Wick', 'Actor')]
            },
            {
                'title': 'Top Gun: Maverick',
                'description': 'After thirty years, Maverick is still pushing the envelope as a top naval aviator, but must confront ghosts of his past.',
                'short_description': 'Maverick trains a new detachment of Top Gun graduates.',
                'release_date': date(2022, 5, 27),
                'duration_minutes': 130,
                'age_certification': 'U/A',
                'language': lang_objs['English'],
                'director': 'Joseph Kosinski',
                'trailer_url': 'https://www.youtube.com/watch?v=giXco2jaZ_4',
                'status': Movie.Status.NOW_SHOWING,
                'genres': [genre_objs['Action'], genre_objs['Drama']],
                'cast': [('Tom Cruise', 'Pete Maverick Mitchell', 'Actor')]
            },
            {
                'title': 'Barbie',
                'description': 'Barbie and Ken are having the time of their lives in the colorful world of Barbie Land before embarking on a journey of self-discovery in the real world.',
                'short_description': 'Barbie and Ken venture into the real world.',
                'release_date': date(2023, 7, 21),
                'duration_minutes': 114,
                'age_certification': 'U/A',
                'language': lang_objs['English'],
                'director': 'Greta Gerwig',
                'trailer_url': 'https://www.youtube.com/watch?v=pBk4NYhWNMM',
                'status': Movie.Status.NOW_SHOWING,
                'genres': [genre_objs['Comedy'], genre_objs['Fantasy']],
                'cast': [('Margot Robbie', 'Barbie', 'Actress'), ('Ryan Gosling', 'Ken', 'Actor')]
            },
            {
                'title': 'Avatar 3: Fire and Ash',
                'description': 'The next chapter in James Cameron’s sci-fi epic saga introducing the Ash People clan of Pandora.',
                'short_description': 'Discover the Ash People clan of Pandora.',
                'release_date': date(2025, 12, 19),
                'duration_minutes': 190,
                'age_certification': 'U/A',
                'language': lang_objs['English'],
                'director': 'James Cameron',
                'trailer_url': 'https://www.youtube.com/watch?v=d9MyW72ELq0',
                'status': Movie.Status.UPCOMING,
                'genres': [genre_objs['Sci-Fi'], genre_objs['Adventure'], genre_objs['Fantasy']],
                'cast': []
            },
            {
                'title': 'The Batman Part II',
                'description': 'Robert Pattinson returns as Batman in the dark superhero mystery thriller sequel.',
                'short_description': 'The Dark Knight returns to protect Gotham City.',
                'release_date': date(2026, 10, 2),
                'duration_minutes': 175,
                'age_certification': '16+',
                'language': lang_objs['English'],
                'director': 'Matt Reeves',
                'trailer_url': 'https://www.youtube.com/watch?v=mqqft2x_Aa4',
                'status': Movie.Status.UPCOMING,
                'genres': [genre_objs['Action'], genre_objs['Crime'], genre_objs['Mystery']],
                'cast': [('Christian Bale', 'Batman', 'Actor')]
            },
            {
                'title': 'Kantara: Chapter 1',
                'description': 'An action drama exploring the mythological origins of the Bhoota Kola tradition.',
                'short_description': 'Mythological origin saga of divine folklore.',
                'release_date': date(2025, 10, 2),
                'duration_minutes': 155,
                'age_certification': 'U/A',
                'language': lang_objs['Kannada'],
                'director': 'Rishab Shetty',
                'trailer_url': 'https://www.youtube.com/watch?v=u5tE-e5n_50',
                'status': Movie.Status.UPCOMING,
                'genres': [genre_objs['Action'], genre_objs['Drama'], genre_objs['Fantasy']],
                'cast': []
            },
            {
                'title': 'Jawan',
                'description': 'A high-octane action thriller detailing the emotional journey of a man driven to rectify wrongs in society.',
                'short_description': 'A vigilante rights the wrongs of society.',
                'release_date': date(2023, 9, 7),
                'duration_minutes': 169,
                'age_certification': 'U/A',
                'language': lang_objs['Hindi'],
                'director': 'Atlee',
                'trailer_url': 'https://www.youtube.com/watch?v=COv52Qyctws',
                'status': Movie.Status.NOW_SHOWING,
                'genres': [genre_objs['Action'], genre_objs['Thriller']],
                'cast': []
            },
            {
                'title': 'Leo',
                'description': 'A mild-mannered cafe owner becomes a local hero, attracting gangsters who claim he is a former syndicate killer.',
                'short_description': 'A cafe owner confronts a criminal syndicate past.',
                'release_date': date(2023, 10, 19),
                'duration_minutes': 164,
                'age_certification': '16+',
                'language': lang_objs['Tamil'],
                'director': 'Lokesh Kanagaraj',
                'trailer_url': 'https://www.youtube.com/watch?v=Po3jStA673E',
                'status': Movie.Status.NOW_SHOWING,
                'genres': [genre_objs['Action'], genre_objs['Crime'], genre_objs['Thriller']],
                'cast': []
            }
        ]

        movie_objs = []
        for mdata in movies_data:
            genres_list = mdata.pop('genres')
            cast_list = mdata.pop('cast')

            movie, _ = Movie.objects.get_or_create(
                slug=slugify(mdata['title']),
                defaults=mdata
            )
            movie.genres.set(genres_list)

            for member_name, char_name, role_name in cast_list:
                if member_name in cast_objs:
                    MovieCast.objects.get_or_create(
                        movie=movie,
                        cast_member=cast_objs[member_name],
                        defaults={'character_name': char_name, 'role': role_name}
                    )

            # Ensure posters and backdrops exist
            if not movie.poster:
                poster_path = f"posters/{movie.slug}_poster.png"
                backdrop_path = f"backdrops/{movie.slug}_backdrop.png"
                movie.poster.name = poster_path
                movie.backdrop_image.name = backdrop_path
                movie.save()

            movie_objs.append(movie)

        self.stdout.write(f"Created/Verified {len(movie_objs)} Movies with Posters.")

        # 6. Theaters & Screens
        ShowSchedule.objects.all().delete()

        theaters_data = [
            ('CinePrime IMAX Megaplex', 'Downtown City Center', '127 Central Avenue', 'New York', 'Parking, IMAX Laser, Dolby Atmos'),
            ('Grand Palace Cinemas', 'Suburban Mall', '45 Grand Boulevard', 'Los Angeles', 'Recliner Seats, Gourmet Food Court'),
            ('CineStar Multiplex', 'Tech Park Mall', '88 Silicon Highway', 'San Francisco', '4DX Motion, Dolby Vision'),
        ]

        created_shows = []
        today = date.today()

        now_showing_movies = [m for m in movie_objs if m.status == Movie.Status.NOW_SHOWING]

        for t_idx, (tname, loc, addr, city, fac) in enumerate(theaters_data):
            theater, _ = Theater.objects.get_or_create(
                name=tname,
                defaults={
                    'location': loc,
                    'address': addr,
                    'city': city,
                    'facilities': fac,
                    'status': Theater.Status.ACTIVE
                }
            )

            # Screens
            s1, _ = Screen.objects.get_or_create(theater=theater, screen_number=1, defaults={'name': 'Screen 1 IMAX', 'capacity': 30, 'screen_type': Screen.ScreenType.IMAX})
            s2, _ = Screen.objects.get_or_create(theater=theater, screen_number=2, defaults={'name': 'Screen 2 Dolby', 'capacity': 30, 'screen_type': Screen.ScreenType.THREE_D})

            # Show Schedules with distinct days/times per screen
            for m_idx, movie in enumerate(now_showing_movies):
                screen = s1 if m_idx % 2 == 0 else s2
                show_date = today + timedelta(days=m_idx)
                start_time = time(10 + (m_idx % 3) * 4, 0)
                end_time = time(13 + (m_idx % 3) * 4, 0)

                existing_show = ShowSchedule.objects.filter(
                    screen=screen,
                    show_date=show_date,
                    start_time=start_time
                ).first()

                if not existing_show:
                    show = ShowSchedule.objects.create(
                        movie=movie,
                        theater=theater,
                        screen=screen,
                        show_date=show_date,
                        start_time=start_time,
                        end_time=end_time,
                        ticket_price=Decimal('14.50'),
                        status=ShowSchedule.Status.OPEN
                    )
                    created_shows.append(show)
                else:
                    created_shows.append(existing_show)

        self.stdout.write(f"Created Theaters, Screens, Seats & {len(created_shows)} Show Schedules.")

        # 7. Sample Booking & Review for Demo User
        if created_shows and demo_user:
            show = created_shows[0]
            seats = list(Seat.objects.filter(screen=show.screen)[:2])
            
            booking, b_created = Booking.objects.get_or_create(
                user=demo_user,
                show=show,
                defaults={
                    'total_amount': Decimal('34.00'),
                    'status': Booking.Status.CONFIRMED,
                    'payment_status': Booking.PaymentStatus.PAID
                }
            )
            if b_created:
                for seat in seats:
                    BookingSeat.objects.create(booking=booking, seat=seat, price=Decimal('14.50'))
                Payment.objects.create(
                    booking=booking,
                    transaction_id=f"TXN-SEED-001",
                    payment_method=Payment.Method.UPI,
                    amount=Decimal('34.00'),
                    payment_status=Payment.Status.SUCCESS
                )

                # Verified Review
                Review.objects.get_or_create(
                    user=demo_user,
                    movie=show.movie,
                    defaults={
                        'booking': booking,
                        'rating': 5,
                        'review_text': 'Absolute masterpiece! Stunning visuals, incredible soundtrack, and unforgettable acting.',
                        'is_verified_viewer': True,
                        'status': Review.Status.APPROVED
                    }
                )
                self.stdout.write("Created Sample Completed Booking & Verified Review.")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
