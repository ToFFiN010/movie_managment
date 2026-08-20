from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/shows/(?P<show_id>\d+)/seats/$', consumers.SeatBookingConsumer.as_asgi()),
]
