import os
import django
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from movies.models import Movie
from config.settings import BASE_DIR

media_dir = BASE_DIR / 'media'
posters_dir = media_dir / 'posters'
backdrops_dir = media_dir / 'backdrops'

os.makedirs(posters_dir, exist_ok=True)
os.makedirs(backdrops_dir, exist_ok=True)

# Color palettes for each movie title
COLOR_PALETTES = {
    'oppenheimer': {'top': (30, 10, 5), 'bottom': (220, 80, 20), 'accent': (255, 180, 50)},
    'dune-part-two': {'top': (40, 25, 10), 'bottom': (210, 130, 40), 'accent': (255, 200, 100)},
    'john-wick-chapter-4': {'top': (15, 15, 25), 'bottom': (180, 20, 40), 'accent': (255, 80, 80)},
    'top-gun-maverick': {'top': (10, 20, 40), 'bottom': (30, 100, 180), 'accent': (100, 200, 255)},
    'barbie': {'top': (60, 10, 50), 'bottom': (240, 60, 180), 'accent': (255, 180, 230)},
    'avatar-3-fire-and-ash': {'top': (5, 25, 40), 'bottom': (0, 150, 200), 'accent': (100, 230, 255)},
    'the-batman-part-ii': {'top': (10, 10, 15), 'bottom': (60, 60, 70), 'accent': (220, 50, 50)},
    'kantara-chapter-1': {'top': (30, 15, 10), 'bottom': (180, 60, 20), 'accent': (255, 160, 40)},
    'jawan': {'top': (25, 20, 15), 'bottom': (190, 70, 30), 'accent': (255, 210, 60)},
    'leo': {'top': (20, 10, 25), 'bottom': (160, 40, 60), 'accent': (255, 120, 140)},
}

def draw_gradient_image(width, height, top_color, bottom_color):
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * (y / height))
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * (y / height))
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img

def create_poster(movie):
    width, height = 600, 900
    palette = COLOR_PALETTES.get(movie.slug, {'top': (15, 23, 42), 'bottom': (245, 158, 11), 'accent': (255, 255, 255)})
    
    img = draw_gradient_image(width, height, palette['top'], palette['bottom'])
    draw = ImageDraw.Draw(img)

    # Outer border
    draw.rectangle([15, 15, width - 15, height - 15], outline=palette['accent'], width=3)
    draw.rectangle([22, 22, width - 22, height - 22], outline=(255, 255, 255, 100), width=1)

    # Decorative headers
    try:
        font_large = ImageFont.truetype("arial.ttf", 38)
        font_medium = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except IOError:
        font_large = font_medium = font_small = ImageFont.load_default()

    # Cinema header tag
    draw.text((width // 2, 60), "CINEPRIME EXCLUSIVE", fill=palette['accent'], anchor="mm", font=font_small)
    
    # Title
    words = movie.title.split()
    if len(words) > 3:
        line1 = " ".join(words[:len(words)//2])
        line2 = " ".join(words[len(words)//2:])
        draw.text((width // 2, height // 2 - 30), line1, fill=(255, 255, 255), anchor="mm", font=font_large)
        draw.text((width // 2, height // 2 + 25), line2, fill=(255, 255, 255), anchor="mm", font=font_large)
    else:
        draw.text((width // 2, height // 2), movie.title, fill=(255, 255, 255), anchor="mm", font=font_large)

    # Details bottom
    director_text = f"DIRECTED BY {movie.director.upper()}"
    draw.text((width // 2, height - 120), director_text, fill=(240, 240, 240), anchor="mm", font=font_small)
    
    meta_text = f"{movie.language.name.upper()}  •  {movie.age_certification}  •  {movie.duration_minutes} MINS"
    draw.text((width // 2, height - 80), meta_text, fill=palette['accent'], anchor="mm", font=font_medium)

    # Status Pill
    status_text = movie.get_status_display().upper()
    draw.rectangle([width // 2 - 100, height - 200, width // 2 + 100, height - 165], fill=(0, 0, 0), outline=palette['accent'], width=2)
    draw.text((width // 2, height - 182), status_text, fill=(255, 255, 255), anchor="mm", font=font_small)

    filename = f"{movie.slug}_poster.png"
    filepath = posters_dir / filename
    img.save(filepath, "PNG")
    return f"posters/{filename}"


def create_backdrop(movie):
    width, height = 1200, 675
    palette = COLOR_PALETTES.get(movie.slug, {'top': (15, 23, 42), 'bottom': (245, 158, 11), 'accent': (255, 255, 255)})
    
    img = draw_gradient_image(width, height, palette['top'], palette['bottom'])
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("arial.ttf", 54)
        font_medium = ImageFont.truetype("arial.ttf", 26)
    except IOError:
        font_large = font_medium = ImageFont.load_default()

    draw.text((width // 2, height // 2 - 20), movie.title.upper(), fill=(255, 255, 255), anchor="mm", font=font_large)
    draw.text((width // 2, height // 2 + 50), f"A FILM BY {movie.director.upper()}", fill=palette['accent'], anchor="mm", font=font_medium)

    filename = f"{movie.slug}_backdrop.png"
    filepath = backdrops_dir / filename
    img.save(filepath, "PNG")
    return f"backdrops/{filename}"


def main():
    movies = Movie.objects.all()
    count = 0
    for movie in movies:
        poster_path = create_poster(movie)
        backdrop_path = create_backdrop(movie)
        movie.poster.name = poster_path
        movie.backdrop_image.name = backdrop_path
        movie.save()
        count += 1
        print(f"Updated media for '{movie.title}': {poster_path}")
    print(f"\nSuccessfully generated and linked posters for {count} movies.")

if __name__ == '__main__':
    main()
