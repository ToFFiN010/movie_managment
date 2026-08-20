import re

def get_youtube_video_id(url):
    """
    Safely extracts ONLY the 11-character YouTube video ID from any YouTube URL format:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - VIDEO_ID itself
    Returns string video_id if valid, or None. Handles '&', '?', '=' safely.
    """
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if url.startswith('javascript:') or url.startswith('data:'):
        return None

    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Check for v= query parameter if present in complex URLs
    v_param = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
    if v_param:
        return v_param.group(1)

    # If the input itself is an 11-character alphanumeric ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    return None

def parse_youtube_id(url):
    """Alias for get_youtube_video_id for backward compatibility."""
    return get_youtube_video_id(url)

def normalize_movie_trailers():
    """
    Database normalization step to clean stored trailer URLs and YouTube IDs.
    Returns count of normalized movie records.
    """
    from movies.models import Movie, MovieTrailer
    count = 0
    for movie in Movie.objects.all():
        raw_source = movie.trailer_url or movie.youtube_video_id
        vid = get_youtube_video_id(raw_source)
        if vid:
            clean_url = f"https://www.youtube.com/watch?v={vid}"
            updated = False
            if movie.youtube_video_id != vid:
                movie.youtube_video_id = vid
                updated = True
            if movie.trailer_url != clean_url:
                movie.trailer_url = clean_url
                updated = True
            if updated:
                movie.save(update_fields=['youtube_video_id', 'trailer_url'])
                count += 1

        # Also clean associated MovieTrailer objects
        for tr in movie.trailers.all():
            tr_vid = get_youtube_video_id(tr.trailer_url or tr.video_id)
            if tr_vid and (tr.video_id != tr_vid or 'embed' in tr.trailer_url):
                tr.video_id = tr_vid
                tr.trailer_url = f"https://www.youtube.com/watch?v={tr_vid}"
                tr.save()

    return count
