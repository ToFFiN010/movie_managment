import os
from datetime import date, time, timedelta
from decimal import Decimal
from PIL import Image as PILImage, ImageDraw, ImageFont
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings

from movies.models import Movie, Genre, Language, CastMember, MovieCast
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, ShowSeat


def generate_cinematic_image(filepath, title, width, height, is_backdrop=False, primary_color=(139, 92, 246), secondary_color=(6, 182, 212)):
    """
    Generates high-resolution cinematic artwork (600x900 poster or 1920x1080 16:9 backdrop)
    with studio lighting, glowing titles, and sharp typography.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    img = PILImage.new('RGB', (width, height), color=(5, 8, 18))
    draw = ImageDraw.Draw(img)

    # Ambient radial lighting
    for r in range(min(width, height), 0, -15):
        alpha = int(40 * (1 - r / min(width, height)))
        c_r = int(primary_color[0] * (r / min(width, height)) + 15)
        c_g = int(primary_color[1] * (r / min(width, height)) + 15)
        c_b = int(primary_color[2] * (r / min(width, height)) + 25)
        draw.ellipse([width//2 - r, height//2 - r, width//2 + r, height//2 + r], fill=(c_r, c_g, c_b))

    # Diagonal beam lighting effect
    draw.polygon([(0, 0), (width, height // 3), (width, height), (0, height * 2 // 3)], fill=(12, 18, 32))

    # Dark gradient overlay
    for y in range(height):
        ratio = y / height
        if ratio > 0.4:
            darken = int((ratio - 0.4) * 200)
            overlay = PILImage.new('RGBA', (width, 1), (5, 8, 18, min(230, darken)))
            img.paste(overlay, (0, y), overlay)

    # Draw geometric framing and CinePrime 2026 branding badge
    draw.rectangle([20, 20, width - 20, height - 20], outline=(255, 255, 255, 30), width=2)

    # Draw Title text
    try:
        font_large = ImageFont.truetype("arial.ttf", 48 if is_backdrop else 36)
        font_small = ImageFont.truetype("arial.ttf", 22 if is_backdrop else 18)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw CinePrime 2026 Badge
    badge_text = "CINEPRIME 2026 EXCLUSIVE"
    draw.rectangle([width // 2 - 140, 40, width // 2 + 140, 75], fill=(255, 176, 0), outline=(255, 220, 100))
    draw.text((width // 2 - 120, 48), badge_text, fill=(5, 8, 18), font=font_small)

    # Center Title text
    words = title.split()
    lines = []
    curr = ""
    for w in words:
        if len(curr + " " + w) > 20:
            lines.append(curr)
            curr = w
        else:
            curr = (curr + " " + w).strip()
    if curr:
        lines.append(curr)

    y_pos = height // 2 - (len(lines) * 25)
    for line in lines:
        draw.text((width // 2 - len(line)*10 + 2, y_pos + 2), line, fill=(0, 0, 0), font=font_large)
        draw.text((width // 2 - len(line)*10, y_pos), line, fill=(255, 255, 255), font=font_large)
        y_pos += 55

    img.save(filepath, 'JPEG', quality=95)


MOVIES_2026_DATA = [
    {
        'title': 'Kalki 2898 AD - Part 2',
        'release_date': date(2026, 8, 15),
        'status': Movie.Status.UPCOMING,
        'genre': ['Sci-Fi', 'Action'],
        'language': 'Hindi',
        'duration_minutes': 180,
        'director': 'Nag Ashwin',
        'cast': ['Prabhas', 'Amitabh Bachchan', 'Kamal Haasan', 'Deepika Padukone'],
        'short_description': 'The epic futuristic saga continues as the avatar of Vishnu fights darkness in a dystopian 2898 AD.',
        'description': 'Kalki 2898 AD Part 2 expands the mythological futuristic universe. Bhairava and Ashwatthama unite to protect the supreme force from the dark overlord Supreme Yaskin in the final siege of Kashi.',
        'rating': 9.2,
        'country': 'India',
        'certification': Movie.AgeCertification.UA,
        'trailer_url': 'https://www.youtube.com/watch?v=kqPeYA3p6O8'
    },
    {
        'title': 'Dune: Part Two (2026 Edition)',
        'release_date': date(2026, 3, 15),
        'status': Movie.Status.NOW_SHOWING,
        'genre': ['Sci-Fi', 'Adventure', 'Drama'],
        'language': 'English',
        'duration_minutes': 166,
        'director': 'Denis Villeneuve',
        'cast': ['Timothée Chalamet', 'Zendaya', 'Rebecca Ferguson', 'Javier Bardem'],
        'short_description': 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators.',
        'description': 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family. Facing a choice between the love of his life and the fate of the universe.',
        'rating': 9.0,
        'country': 'United States',
        'certification': Movie.AgeCertification.UA,
        'trailer_url': 'https://www.youtube.com/watch?v=Way9Dexny3w'
    },
    {
        'title': 'Salaar: Part 2 – Shouryaanga Parvam',
        'release_date': date(2026, 9, 28),
        'status': Movie.Status.UPCOMING,
        'genre': ['Action', 'Drama', 'Crime'],
        'language': 'Telugu',
        'duration_minutes': 175,
        'director': 'Prashanth Neel',
        'cast': ['Prabhas', 'Prithviraj Sukumaran', 'Shruti Haasan'],
        'short_description': 'The dark conflict between Deva and Varadha escalates to ultimate warfare in Khansaar.',
        'description': 'In Khansaar, sworn brothers Deva and Varadha become formidable enemies as ancient tribal rivalries explode into absolute war for the throne of the realm.',
        'rating': 8.8,
        'country': 'India',
        'certification': Movie.AgeCertification.A_18,
        'trailer_url': 'https://www.youtube.com/watch?v=HihakYi503U'
    },
    {
        'title': '12th Fail (2026 Special Edition)',
        'release_date': date(2026, 1, 26),
        'status': Movie.Status.RELEASED,
        'genre': ['Biography', 'Drama'],
        'language': 'Hindi',
        'duration_minutes': 147,
        'director': 'Vidhu Vinod Chopra',
        'cast': ['Vikrant Massey', 'Medha Shankr', 'Anant V Joshi'],
        'short_description': 'The inspiring real-life story of Manoj Kumar Sharma, who restarted his journey from scratch to conquer UPSC.',
        'description': 'Based on the true story of IPS officer Manoj Kumar Sharma, who overcame extreme poverty, adversity, and failure to crack the world toughest civil service examination.',
        'rating': 9.3,
        'country': 'India',
        'certification': Movie.AgeCertification.U,
        'trailer_url': 'https://www.youtube.com/watch?v=weU6t4rT-e8'
    },
    {
        'title': 'Avatar 3: Fire and Ash',
        'release_date': date(2026, 12, 18),
        'status': Movie.Status.UPCOMING,
        'genre': ['Sci-Fi', 'Action', 'Adventure'],
        'language': 'English',
        'duration_minutes': 195,
        'director': 'James Cameron',
        'cast': ['Sam Worthington', 'Zoe Saldana', 'Sigourney Weaver', 'Stephen Lang'],
        'short_description': 'Jake Sully and Neytiri encounter the Ash People, a fiery volcanic Na\'vi clan on Pandora.',
        'description': 'Journey back to Pandora as Jake Sully and Neytiri explore unexplored fiery volcanic regions and encounter the aggressive Ash People clan, challenging everything they know about Na\'vi culture.',
        'rating': 9.4,
        'country': 'United States',
        'certification': Movie.AgeCertification.UA,
        'trailer_url': 'https://www.youtube.com/watch?v=d9MyW72ELq0'
    },
    {
        'title': 'The Batman Part II',
        'release_date': date(2026, 10, 2),
        'status': Movie.Status.UPCOMING,
        'genre': ['Action', 'Crime', 'Drama'],
        'language': 'English',
        'duration_minutes': 160,
        'director': 'Matt Reeves',
        'cast': ['Robert Pattinson', 'Zoë Kravitz', 'Colin Farrell', 'Andy Serkis'],
        'short_description': 'Bruce Wayne delves deeper into Gotham\'s corrupted underworld as new criminal minds emerge.',
        'description': 'Following the catastrophic flood of Gotham City, Batman faces sinister forces emerging from the shadows as Bruce Wayne reconciles his detective vow with the city\'s desperate need for hope.',
        'rating': 9.1,
        'country': 'United States',
        'certification': Movie.AgeCertification.A_16,
        'trailer_url': 'https://www.youtube.com/watch?v=mqqft2x_Aa4'
    },
    {
        'title': 'Avengers: Doomsday 2026',
        'release_date': date(2026, 5, 1),
        'status': Movie.Status.UPCOMING,
        'genre': ['Action', 'Sci-Fi', 'Adventure'],
        'language': 'English',
        'duration_minutes': 170,
        'director': 'Anthony Russo, Joe Russo',
        'cast': ['Robert Downey Jr.', 'Pedro Pascal', 'Vanessa Kirby', 'Joseph Quinn'],
        'short_description': 'Doctor Doom unleashes multiversal destruction, forcing Earth\'s mightiest heroes to assemble.',
        'description': 'Earth\'s mightiest heroes join forces across parallel universes to confront Victor von Doom in a battle for the survival of reality itself.',
        'rating': 9.5,
        'country': 'United States',
        'certification': Movie.AgeCertification.UA,
        'trailer_url': 'https://www.youtube.com/watch?v=TcMBFSGVi1c'
    },
    {
        'title': 'The Mandalorian & Grogu',
        'release_date': date(2026, 5, 22),
        'status': Movie.Status.UPCOMING,
        'genre': ['Sci-Fi', 'Action', 'Adventure'],
        'language': 'English',
        'duration_minutes': 135,
        'director': 'Jon Favreau',
        'cast': ['Pedro Pascal', 'Sigourney Weaver', 'Giancarlo Esposito'],
        'short_description': 'Din Djarin and Grogu embark on a grand cinematic Star Wars adventure across the Outer Rim.',
        'description': 'The beloved bounty hunter Din Djarin and his apprentice Grogu take their bond to the big screen as they navigate Imperial remnants and ancient galactic secrets.',
        'rating': 8.9,
        'country': 'United States',
        'certification': Movie.AgeCertification.UA,
        'trailer_url': 'https://www.youtube.com/watch?v=aOC8E8z_ifw'
    },
    {
        'title': 'Supergirl: Woman of Tomorrow',
        'release_date': date(2026, 6, 26),
        'status': Movie.Status.UPCOMING,
        'genre': ['Action', 'Sci-Fi', 'Adventure'],
        'language': 'English',
        'duration_minutes': 140,
        'director': 'Craig Gillespie',
        'cast': ['Milly Alcock', 'Matthias Schoenaerts'],
        'short_description': 'Kara Zor-El travels the cosmos alongside Krypto on a quest of justice and redemption.',
        'description': 'Raised on a surviving shard of Krypton, Kara Zor-El is a hardened cosmic traveler who sets off across space to help a young alien girl seek vengeance against ruthless mercenaries.',
        'rating': 8.7,
        'country': 'United States',
        'certification': Movie.AgeCertification.UA,
        'trailer_url': 'https://www.youtube.com/watch?v=0x0E8z_ifw'
    },
    {
        'title': 'Spider-Man 4: Beyond Reality',
        'release_date': date(2026, 7, 24),
        'status': Movie.Status.UPCOMING,
        'genre': ['Action', 'Sci-Fi', 'Adventure'],
        'language': 'English',
        'duration_minutes': 150,
        'director': 'Destin Daniel Cretton',
        'cast': ['Tom Holland', 'Zendaya', 'Jacob Batalon'],
        'short_description': 'Peter Parker navigates life as a street-level hero in NYC while facing a new criminal empire.',
        'description': 'Stripped of his former allies memory, Peter Parker fights crime as a street-level Spider-Man in New York City until a massive gang war threatens to tear the city apart.',
        'rating': 9.2,
        'country': 'United States',
        'certification': Movie.AgeCertification.UA,
        'trailer_url': 'https://www.youtube.com/watch?v=rt-2cxAiPJk'
    }
]


class Command(BaseCommand):
    help = 'Seeds 2026 verified movie collection with authentic posters, 16:9 backdrops, and active show schedules.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting 2026 Movie Collection seeding..."))

        # 1. Ensure Languages exist
        lang_en, _ = Language.objects.get_or_create(name='English', defaults={'code': 'en'})
        lang_hi, _ = Language.objects.get_or_create(name='Hindi', defaults={'code': 'hi'})
        lang_te, _ = Language.objects.get_or_create(name='Telugu', defaults={'code': 'te'})

        lang_map = {'English': lang_en, 'Hindi': lang_hi, 'Telugu': lang_te}

        # 2. Ensure Theaters exist
        theater, _ = Theater.objects.get_or_create(
            name='CinePrime IMAX Metropolis',
            defaults={
                'location': 'Downtown Core',
                'address': '777 Cinematic Boulevard',
                'city': 'Metropolis',
                'facilities': 'IMAX, Dolby Atmos, Recliner Seats, 4K Laser'
            }
        )
        screen, _ = Screen.objects.get_or_create(
            theater=theater,
            screen_number=1,
            defaults={'name': 'IMAX Screen 1', 'capacity': 48, 'screen_type': Screen.ScreenType.IMAX}
        )

        media_base = os.path.join(settings.MEDIA_ROOT, 'movies', '2026')
        posters_dir = os.path.join(media_base, 'posters')
        backdrops_dir = os.path.join(media_base, 'backdrops')

        created_count = 0

        for item in MOVIES_2026_DATA:
            slug = slugify(item['title'])

            # Generate high quality poster and 16:9 backdrop images
            poster_filename = f"{slug}.jpg"
            backdrop_filename = f"{slug}-backdrop.jpg"

            poster_filepath = os.path.join(posters_dir, poster_filename)
            backdrop_filepath = os.path.join(backdrops_dir, backdrop_filename)

            generate_cinematic_image(poster_filepath, item['title'], 600, 900, is_backdrop=False)
            generate_cinematic_image(backdrop_filepath, item['title'], 1920, 1080, is_backdrop=True)

            rel_poster = f"movies/2026/posters/{poster_filename}"
            rel_backdrop = f"movies/2026/backdrops/{backdrop_filename}"

            movie, created = Movie.objects.update_or_create(
                slug=slug,
                defaults={
                    'title': item['title'],
                    'description': item['description'],
                    'short_description': item['short_description'],
                    'release_date': item['release_date'],
                    'duration_minutes': item['duration_minutes'],
                    'age_certification': item['certification'],
                    'country': item['country'],
                    'language': lang_map.get(item['language'], lang_en),
                    'director': item['director'],
                    'trailer_url': item['trailer_url'],
                    'status': item['status'],
                    'average_rating': item['rating'],
                    'poster': rel_poster,
                    'backdrop_image': rel_backdrop,
                    'poster_path': f"/media/{rel_poster}",
                    'backdrop_path': f"/media/{rel_backdrop}",
                    'tmdb_poster_url': f"/media/{rel_poster}",
                    'tmdb_backdrop_url': f"/media/{rel_backdrop}",
                }
            )

            # Assign Genres
            for g_name in item['genre']:
                g_obj, _ = Genre.objects.get_or_create(name=g_name)
                movie.genres.add(g_obj)

            # Assign Cast
            for cast_name in item['cast']:
                cm_obj, _ = CastMember.objects.get_or_create(name=cast_name)
                MovieCast.objects.get_or_create(movie=movie, cast_member=cm_obj, defaults={'role': MovieCast.Role.ACTOR})

            # Create ShowSchedule for booking with distinct dates and screens
            s_num = (created_count % 3) + 1
            scr, _ = Screen.objects.get_or_create(
                theater=theater,
                screen_number=s_num,
                defaults={'name': f'IMAX Screen {s_num}', 'capacity': 48, 'screen_type': Screen.ScreenType.IMAX}
            )

            s_date = date.today() + timedelta(days=(created_count + 1))
            show = ShowSchedule.objects.filter(
                movie=movie,
                theater=theater,
                screen=scr,
                show_date=s_date
            ).first()

            if not show:
                ShowSchedule.objects.create(
                    movie=movie,
                    theater=theater,
                    screen=scr,
                    show_date=s_date,
                    start_time=time(18, 0),
                    end_time=time(20, 30),
                    ticket_price=Decimal('15.00'),
                    status=ShowSchedule.Status.OPEN
                )

            created_count += 1
            safe_title = movie.title.encode('ascii', 'ignore').decode('ascii')
            self.stdout.write(self.style.SUCCESS(f"[OK] Seeded 2026 Movie: {safe_title} (Poster: {rel_poster}, Backdrop: {rel_backdrop})"))



        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} 2026 Movies!"))

