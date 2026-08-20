import os
import urllib.request
import urllib.parse
import json
from django.conf import settings

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"

def get_api_key():
    return os.getenv('TMDB_API_KEY') or getattr(settings, 'TMDB_API_KEY', None)

def search_tmdb_movie(title, release_year=None):
    """
    Queries TMDB API for a movie title and returns movie metadata dictionary including:
    - tmdb_id
    - poster_url (w500)
    - backdrop_url (w1280)
    - vote_average
    - overview
    """
    api_key = get_api_key()
    if not api_key or api_key == 'sample_tmdb_api_key_placeholder':
        # Curated TMDb catalog mapping for offline / unconfigured API keys
        curated_map = {
            'oppenheimer': {'tmdb_id': 872585, 'poster_path': '/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg'},
            'dune part two': {'tmdb_id': 693134, 'poster_path': '/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg'},
            'john wick chapter 4': {'tmdb_id': 603692, 'poster_path': '/vZloFAK7NMVMGKE7VkF5UHaz0I.jpg'},
            'top gun maverick': {'tmdb_id': 361743, 'poster_path': '/62HCfaYToWd2LbtmUv4CXHQuAVS.jpg'},
            'barbie': {'tmdb_id': 346698, 'poster_path': '/iuFNMS8U5cb6xfzi51utuvchvN.jpg'},
            'the shawshank redemption': {'tmdb_id': 278, 'poster_path': '/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg'},
            'interstellar': {'tmdb_id': 157336, 'poster_path': '/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg'},
            'the dark knight': {'tmdb_id': 155, 'poster_path': '/qJ2tW6WMUDux911r6m7haRef0WH.jpg'},
            'avatar 3': {'tmdb_id': 8358, 'poster_path': '/media/movies/posters/avatar-3-fire-and-ash.jpg'},
            'avatar 3 fire and ash': {'tmdb_id': 8358, 'poster_path': '/media/movies/posters/avatar-3-fire-and-ash.jpg'},
            'the batman part ii': {'tmdb_id': 414906, 'poster_path': '/media/movies/posters/the-batman-part-ii-poster.jpg'},
            'kantara chapter 1': {'tmdb_id': 1184918, 'poster_path': '/media/movies/posters/kantara-chapter-1-poster.jpg'},
            'jawan': {'tmdb_id': 872906, 'poster_path': '/media/movies/posters/jawan-poster.jpg'},
            'leo': {'tmdb_id': 980489, 'poster_path': '/media/movies/posters/leo-poster.jpg'},
            'salaar': {'tmdb_id': 781732, 'poster_path': '/media/movies/posters/salaar-poster.jpg'},
            'kgf chapter 2': {'tmdb_id': 580489, 'poster_path': '/media/movies/posters/kgf-chapter-2-poster.jpg'},
            '12th fail': {'tmdb_id': 1152064, 'poster_path': '/media/movies/posters/12th-fail-poster.jpg'},
            'kalki 2898 ad': {'tmdb_id': 76341, 'poster_path': '/media/movies/posters/kalki-2898-ad-poster.jpg'},
            'avengers doomsday': {'tmdb_id': 1003596, 'poster_path': '/media/movies/posters/avengers-doomsday-2026-poster.jpg'},
            'the mandalorian & grogu': {'tmdb_id': 1222248, 'poster_path': '/media/movies/posters/the-mandalorian-grogu-poster.jpg'},
            'supergirl woman of tomorrow': {'tmdb_id': 1171640, 'poster_path': '/media/movies/posters/supergirl-woman-of-tomorrow-poster.jpg'},
            'spider man brand new day': {'tmdb_id': 939243, 'poster_path': '/media/movies/posters/spider-man-brand-new-day-poster.webp'},
        }

        t_clean = urllib.parse.unquote(title).lower().replace(':', '').replace('-', ' ').strip()
        for k, v in curated_map.items():
            if k in t_clean or t_clean in k:
                if isinstance(v, dict):
                    p_path = v['poster_path']
                    t_id = v['tmdb_id']
                else:
                    p_path = f"/{v}.jpg"
                    t_id = 999999
                p_url = f"{TMDB_POSTER_BASE}{p_path}" if not p_path.startswith('http') and not p_path.startswith('/media/') else p_path
                return {
                    'tmdb_id': t_id,
                    'poster_path': p_path,
                    'backdrop_path': None,
                    'poster_url': p_url,
                    'backdrop_url': None,
                    'title': title,
                    'vote_average': 8.5,
                    'overview': f"Official overview for {title}.",
                }
        return None

    try:
        encoded_query = urllib.parse.quote(title)
        url = f"{TMDB_API_BASE}/search/movie?api_key={api_key}&query={encoded_query}"
        if release_year:
            url += f"&year={release_year}"

        req = urllib.request.Request(url, headers={'User-Agent': 'CinePrime/1.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                results = data.get('results', [])
                if not results:
                    return None

                # Find best matching result
                result = results[0]
                poster_path = result.get('poster_path')
                backdrop_path = result.get('backdrop_path')

                return {
                    'tmdb_id': result.get('id'),
                    'poster_path': poster_path,
                    'backdrop_path': backdrop_path,
                    'poster_url': f"{TMDB_POSTER_BASE}{poster_path}" if poster_path else None,
                    'backdrop_url': f"{TMDB_BACKDROP_BASE}{backdrop_path}" if backdrop_path else None,
                    'title': result.get('title'),
                    'vote_average': result.get('vote_average'),
                    'overview': result.get('overview'),
                }
    except Exception as e:
        print(f"TMDB API query error for '{title}': {e}")
        return None

    return None


def get_poster_url(poster_path):
    if not poster_path:
        return '/media/movies/posters/cineprime_default_fallback.png'
    if poster_path.startswith('http://') or poster_path.startswith('https://'):
        return poster_path
    return f"{TMDB_POSTER_BASE}{poster_path}"


def get_backdrop_url(backdrop_path):
    if not backdrop_path:
        return None
    if backdrop_path.startswith('http://') or backdrop_path.startswith('https://'):
        return backdrop_path
    return f"{TMDB_BACKDROP_BASE}{backdrop_path}"


def search_movie(title, year=None):
    return search_tmdb_movie(title, release_year=year)


def get_tmdb_movie_details(tmdb_id):
    """
    Fetches detailed metadata for a specific TMDB ID.
    """
    api_key = get_api_key()
    if not api_key or not tmdb_id:
        return None

    try:
        url = f"{TMDB_API_BASE}/movie/{tmdb_id}?api_key={api_key}"
        req = urllib.request.Request(url, headers={'User-Agent': 'CinePrime/1.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                poster_path = data.get('poster_path')
                backdrop_path = data.get('backdrop_path')
                return {
                    'tmdb_id': data.get('id'),
                    'poster_url': f"{TMDB_POSTER_BASE}{poster_path}" if poster_path else None,
                    'backdrop_url': f"{TMDB_BACKDROP_BASE}{backdrop_path}" if backdrop_path else None,
                    'runtime': data.get('runtime'),
                    'tagline': data.get('tagline'),
                    'vote_average': data.get('vote_average'),
                }
    except Exception as e:
        print(f"TMDB API details error for ID {tmdb_id}: {e}")
        return None

    return None


def get_movie_images(tmdb_id):
    details = get_tmdb_movie_details(tmdb_id)
    if details:
        return {
            'poster_url': details.get('poster_url'),
            'backdrop_url': details.get('backdrop_url')
        }
    return None


