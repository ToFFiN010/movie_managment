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


