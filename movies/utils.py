import re

def parse_youtube_id(url):
    """
    Extracts and validates YouTube video ID from various YouTube URL formats.
    Returns string video_id if valid, or None.
    Prevents raw iframe HTML injection.
    """
    if not url:
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
    
    # If the string itself is a 11-char alphanumeric ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()):
        return url.strip()

    return None
