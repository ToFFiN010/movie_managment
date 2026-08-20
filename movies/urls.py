from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    path('', views.movie_listing_view, name='listing'),
    path('movies/', views.movie_listing_view, name='all_movies'),
    path('theaters/', views.theaters_view, name='theaters'),
    path('search/', views.search_view, name='search'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('watchlist/toggle/<int:movie_id>/', views.watchlist_toggle_view, name='watchlist_toggle'),
    path('api/detail/<int:movie_id>/', views.movie_api_detail, name='api_detail'),
    path('api/search_suggestions/', views.search_suggestions_api, name='api_search_suggestions'),
    path('<slug:slug>/', views.movie_detail_view, name='detail'),
]

