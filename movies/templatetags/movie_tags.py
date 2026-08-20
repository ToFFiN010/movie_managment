from django import template
from movies.utils import get_youtube_video_id

register = template.Library()

@register.filter(name='get_youtube_id')
def get_youtube_id_filter(value):
    return get_youtube_video_id(value) or ''

@register.filter(name='get_youtube_embed_url')
def get_youtube_embed_url_filter(value):
    vid = get_youtube_video_id(value)
    if vid:
        return f"https://www.youtube.com/embed/{vid}?rel=0&modestbranding=1"
    return ''
