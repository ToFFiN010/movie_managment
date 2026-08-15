import os
import math
import django
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from movies.models import Movie, Genre, Language
from config.settings import BASE_DIR

media_dir = BASE_DIR / 'media'
posters_dir = media_dir / 'posters'
backdrops_dir = media_dir / 'backdrops'

os.makedirs(posters_dir, exist_ok=True)
os.makedirs(backdrops_dir, exist_ok=True)

# Generate Default Professional CinePrime Fallback Poster
def generate_default_fallback():
    width, height = 600, 900
    img = Image.new('RGB', (width, height), (7, 11, 18))
    draw = ImageDraw.Draw(img)

    # Vignette & Glow
    for r in range(400, 0, -2):
        alpha = int(35 * (1 - r / 400))
        draw.ellipse([width//2 - r, height//2 - r, width//2 + r, height//2 + r], fill=(255, 176, 0, alpha))

    # Gold borders
    draw.rectangle([20, 20, width - 20, height - 20], outline=(255, 176, 0), width=3)
    draw.rectangle([28, 28, width - 28, height - 28], outline=(255, 255, 255, 80), width=1)

    try:
        font_logo = ImageFont.truetype("arial.ttf", 44)
        font_sub = ImageFont.truetype("arial.ttf", 28)
        font_tag = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font_logo = font_sub = font_tag = ImageFont.load_default()

    # Film strip graphics top & bottom
    for x in range(40, width - 40, 40):
        draw.rectangle([x, 40, x + 24, 60], fill=(255, 176, 0))
        draw.rectangle([x, height - 60, x + 24, height - 40], fill=(255, 176, 0))

    draw.text((width // 2, height // 2 - 40), "CINEPRIME", fill=(255, 176, 0), anchor="mm", font=font_logo)
    draw.text((width // 2, height // 2 + 20), "OFFICIAL MOVIE", fill=(255, 255, 255), anchor="mm", font=font_sub)
    draw.text((width // 2, height // 2 + 70), "PREMIUM CINEMA SELECTION", fill=(156, 167, 183), anchor="mm", font=font_tag)

    fallback_path = posters_dir / 'cineprime_default_fallback.png'
    img.save(fallback_path, 'PNG')
    print("Generated CinePrime Default Fallback Poster.")

# Colors and Visual Themes per Movie
MOVIE_ARTWORK_THEMES = {
    'oppenheimer': {'base': (15, 5, 2), 'glow': (240, 90, 10), 'accent': (255, 190, 40), 'tagline': 'THE WORLD FOREVER CHANGES'},
    'dune-part-two': {'base': (25, 12, 5), 'glow': (220, 140, 30), 'accent': (255, 210, 90), 'tagline': 'LONG LIVE THE FIGHTERS'},
    'salaar': {'base': (10, 10, 12), 'glow': (150, 30, 20), 'accent': (255, 80, 60), 'tagline': 'THE MOST VIOLENT MAN'},
    'kgf-chapter-2': {'base': (20, 15, 5), 'glow': (210, 160, 20), 'accent': (255, 215, 0), 'tagline': 'MONSTER IS BACK'},
    'john-wick-chapter-4': {'base': (10, 10, 20), 'glow': (180, 20, 50), 'accent': (255, 90, 120), 'tagline': 'NO WAY OUT'},
    'top-gun-maverick': {'base': (5, 15, 35), 'glow': (30, 120, 210), 'accent': (120, 220, 255), 'tagline': 'FEEL THE NEED FOR SPEED'},
    'barbie': {'base': (40, 5, 35), 'glow': (240, 50, 160), 'accent': (255, 180, 230), 'tagline': 'SHE CAN DO ANYTHING'},
    'jawan': {'base': (20, 12, 8), 'glow': (200, 60, 20), 'accent': (255, 200, 50), 'tagline': 'READY OR NOT'},
    'leo': {'base': (15, 8, 20), 'glow': (160, 30, 70), 'accent': (255, 110, 140), 'tagline': 'BLOOD & SWEET'},
    'interstellar': {'base': (2, 8, 20), 'glow': (20, 100, 180), 'accent': (140, 210, 255), 'tagline': 'MANKIND WAS BORN ON EARTH'},
    'the-dark-knight': {'base': (5, 8, 12), 'glow': (80, 100, 120), 'accent': (255, 255, 255), 'tagline': 'WHY SO SERIOUS?'},
    '12th-fail': {'base': (15, 20, 15), 'glow': (40, 160, 80), 'accent': (160, 240, 140), 'tagline': 'RESTART YOUR DREAMS'},
    'the-shawshank-redemption': {'base': (12, 18, 25), 'glow': (60, 120, 160), 'accent': (220, 230, 250), 'tagline': 'FEAR CAN HOLD YOU PRISONER'},
    'avatar-3-fire-and-ash': {'base': (2, 20, 30), 'glow': (0, 160, 210), 'accent': (100, 240, 255), 'tagline': 'ENTER THE ASH KINGDOM'},
    'the-batman-part-ii': {'base': (8, 5, 8), 'glow': (180, 30, 30), 'accent': (255, 80, 80), 'tagline': 'UNMASK THE TRUTH'},
    'kantara-chapter-1': {'base': (25, 10, 5), 'glow': (210, 90, 20), 'accent': (255, 180, 50), 'tagline': 'DIVINE LEGEND UNFOLDS'},
}

def create_cinema_poster(movie):
    width, height = 600, 900
    theme = MOVIE_ARTWORK_THEMES.get(movie.slug, {
        'base': (10, 15, 25), 'glow': (210, 160, 20), 'accent': (255, 215, 0), 'tagline': 'A CINEMATIC MASTERPIECE'
    })

    img = Image.new('RGB', (width, height), theme['base'])
    draw = ImageDraw.Draw(img)

    # Dynamic Spotlight Effect
    for r in range(450, 0, -3):
        alpha = int(40 * (1 - r / 450))
        draw.ellipse([width//2 - r, height//3 - r, width//2 + r, height//3 + r], fill=(theme['glow'][0], theme['glow'][1], theme['glow'][2], alpha))

    # Border Framing
    draw.rectangle([16, 16, width - 16, height - 16], outline=theme['accent'], width=2)
    draw.rectangle([24, 24, width - 24, height - 24], outline=(255, 255, 255, 60), width=1)

    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_tag = ImageFont.truetype("arial.ttf", 16)
        font_meta = ImageFont.truetype("arial.ttf", 18)
        font_brand = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font_title = font_tag = font_meta = font_brand = ImageFont.load_default()

    # Brand Header
    draw.text((width // 2, 50), "CINEPRIME CINEMAS", fill=theme['accent'], anchor="mm", font=font_brand)

    # Tagline
    draw.text((width // 2, 130), f"“ {theme['tagline']} ”", fill=(220, 220, 220), anchor="mm", font=font_tag)

    # Title Box in Center
    words = movie.title.upper().split()
    if len(words) >= 3:
        line1 = " ".join(words[:len(words)//2])
        line2 = " ".join(words[len(words)//2:])
        draw.text((width // 2, height // 2 - 25), line1, fill=(255, 255, 255), anchor="mm", font=font_title)
        draw.text((width // 2, height // 2 + 25), line2, fill=(255, 255, 255), anchor="mm", font=font_title)
    else:
        draw.text((width // 2, height // 2), movie.title.upper(), fill=(255, 255, 255), anchor="mm", font=font_title)

    # Footer Metadata
    director_text = f"DIRECTED BY {movie.director.upper()}"
    draw.text((width // 2, height - 130), director_text, fill=(200, 200, 200), anchor="mm", font=font_tag)

    meta_str = f"{movie.language.name.upper()}  •  {movie.age_certification}  •  {movie.duration_minutes}M"
    draw.text((width // 2, height - 90), meta_str, fill=theme['accent'], anchor="mm", font=font_meta)

    filename = f"{movie.slug}_poster.png"
    filepath = posters_dir / filename
    img.save(filepath, 'PNG')
    return f"posters/{filename}"

def create_cinema_backdrop(movie):
    width, height = 1200, 675
    theme = MOVIE_ARTWORK_THEMES.get(movie.slug, {
        'base': (10, 15, 25), 'glow': (210, 160, 20), 'accent': (255, 215, 0), 'tagline': 'A CINEMATIC MASTERPIECE'
    })

    img = Image.new('RGB', (width, height), theme['base'])
    draw = ImageDraw.Draw(img)

    for r in range(600, 0, -4):
        alpha = int(45 * (1 - r / 600))
        draw.ellipse([width//2 - r, height//2 - r, width//2 + r, height//2 + r], fill=(theme['glow'][0], theme['glow'][1], theme['glow'][2], alpha))

    try:
        font_large = ImageFont.truetype("arial.ttf", 52)
        font_sub = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font_large = font_sub = ImageFont.load_default()

    draw.text((width // 2, height // 2 - 30), movie.title.upper(), fill=(255, 255, 255), anchor="mm", font=font_large)
    draw.text((width // 2, height // 2 + 40), f"A FILM BY {movie.director.upper()}", fill=theme['accent'], anchor="mm", font=font_sub)

    filename = f"{movie.slug}_backdrop.png"
    filepath = backdrops_dir / filename
    img.save(filepath, 'PNG')
    return f"backdrops/{filename}"

def main():
    generate_default_fallback()

    # Ensure required languages & genres exist
    lang_en, _ = Language.objects.get_or_create(name='English', defaults={'code': 'en'})
    lang_hi, _ = Language.objects.get_or_create(name='Hindi', defaults={'code': 'hi'})
    lang_te, _ = Language.objects.get_or_create(name='Telugu', defaults={'code': 'te'})
    lang_kn, _ = Language.objects.get_or_create(name='Kannada', defaults={'code': 'kn'})

    g_action, _ = Genre.objects.get_or_create(name='Action')
    g_drama, _ = Genre.objects.get_or_create(name='Drama')
    g_scifi, _ = Genre.objects.get_or_create(name='Sci-Fi')
    g_crime, _ = Genre.objects.get_or_create(name='Crime')

    # Ensure missing requested movies are created cleanly
    additional_movies = [
        {
            'title': 'Salaar', 'description': 'A gang leader makes a promise to a dying friend and takes on other criminal gangs.',
            'short_description': 'A gang leader takes on criminal syndicates.', 'release_date': date(2023, 12, 22),
            'duration_minutes': 175, 'age_certification': '16+', 'language': lang_te, 'director': 'Prashanth Neel',
            'status': Movie.Status.NOW_SHOWING, 'average_rating': 8.2, 'genres': [g_action, g_crime]
        },
        {
            'title': 'KGF: Chapter 2', 'description': 'Rocky takes control of the Kolar Gold Fields and faces ferocious rivals.',
            'short_description': 'Rocky rules the gold fields.', 'release_date': date(2022, 4, 14),
            'duration_minutes': 168, 'age_certification': 'UA', 'language': lang_kn, 'director': 'Prashanth Neel',
            'status': Movie.Status.NOW_SHOWING, 'average_rating': 8.5, 'genres': [g_action, g_drama]
        },
        {
            'title': 'Interstellar', 'description': 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity survival.',
            'short_description': 'Explorers travel through a space wormhole.', 'release_date': date(2014, 11, 7),
            'duration_minutes': 169, 'age_certification': '13+', 'language': lang_en, 'director': 'Christopher Nolan',
            'status': Movie.Status.NOW_SHOWING, 'average_rating': 8.7, 'genres': [g_scifi, g_drama]
        },
        {
            'title': 'The Dark Knight', 'description': 'When the menace known as the Joker wreaks havoc and chaos on Gotham City, Batman must accept his test.',
            'short_description': 'Batman faces the Joker in Gotham.', 'release_date': date(2008, 7, 18),
            'duration_minutes': 152, 'age_certification': '16+', 'language': lang_en, 'director': 'Christopher Nolan',
            'status': Movie.Status.NOW_SHOWING, 'average_rating': 9.0, 'genres': [g_action, g_crime]
        },
        {
            'title': '12th Fail', 'description': 'Inspired by real stories, an IPS officer restarts his journey to clear the tough civil services exams.',
            'short_description': 'An IPS officer restarts his dream journey.', 'release_date': date(2023, 10, 27),
            'duration_minutes': 147, 'age_certification': 'U', 'language': lang_hi, 'director': 'Vidhu Vinod Chopra',
            'status': Movie.Status.NOW_SHOWING, 'average_rating': 8.8, 'genres': [g_drama]
        },
        {
            'title': 'The Shawshank Redemption', 'description': 'Two imprisoned men bond over a number of years, finding solace and eventual redemption.',
            'short_description': 'Two prisoners bond over solace and redemption.', 'release_date': date(1994, 9, 22),
            'duration_minutes': 142, 'age_certification': '16+', 'language': lang_en, 'director': 'Frank Darabont',
            'status': Movie.Status.NOW_SHOWING, 'average_rating': 9.3, 'genres': [g_drama]
        }
    ]

    for mdata in additional_movies:
        genres_list = mdata.pop('genres')
        movie, _ = Movie.objects.get_or_create(
            title=mdata['title'],
            defaults=mdata
        )
        movie.genres.set(genres_list)

    movies = Movie.objects.all()
    count = 0
    for movie in movies:
        poster_path = create_cinema_poster(movie)
        backdrop_path = create_cinema_backdrop(movie)
        movie.poster.name = poster_path
        movie.backdrop_image.name = backdrop_path
        movie.save()
        count += 1
        print(f"Generated & linked artwork for '{movie.title}': {poster_path}")

    print(f"\nSuccessfully created cinema poster artwork for all {count} movies.")

if __name__ == '__main__':
    main()
