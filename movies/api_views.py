from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import Movie, Genre, Language
from .serializers import (
    MovieSerializer, GenreSerializer, LanguageSerializer,
    TheaterSerializer, ShowScheduleSerializer, BookingSerializer, ReviewSerializer
)
from theaters.models import Theater
from bookings.models import ShowSchedule, Booking
from reviews.models import Review
from recommendations.services import get_similar_movies, get_trending_movies

class MovieListAPIView(generics.ListAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    filterset_fields = ['status', 'language', 'genres', 'age_certification']
    search_fields = ['title', 'director']

class MovieDetailAPIView(generics.RetrieveAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

@api_view(['GET'])
def trending_movies_api(request):
    trending = get_trending_movies(limit=10)
    serializer = MovieSerializer(trending, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def recent_movies_api(request):
    recent = Movie.objects.order_by('-release_date')[:10]
    serializer = MovieSerializer(recent, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def similar_movies_api(request, pk):
    try:
        movie = Movie.objects.get(pk=pk)
    except Movie.DoesNotExist:
        return Response({'error': 'Movie not found'}, status=404)
    similar = get_similar_movies(movie, limit=6)
    serializer = MovieSerializer(similar, many=True, context={'request': request})
    return Response(serializer.data)

class GenreListAPIView(generics.ListAPIView):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer

class LanguageListAPIView(generics.ListAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer

class TheaterListAPIView(generics.ListAPIView):
    queryset = Theater.objects.filter(status=Theater.Status.ACTIVE)
    serializer_class = TheaterSerializer

class ShowScheduleListAPIView(generics.ListAPIView):
    queryset = ShowSchedule.objects.all()
    serializer_class = ShowScheduleSerializer
    filterset_fields = ['movie', 'theater', 'show_date', 'status']

class BookingListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

class ReviewListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        movie_id = self.request.query_params.get('movie_id')
        if movie_id:
            return Review.objects.filter(movie_id=movie_id, status=Review.Status.APPROVED)
        return Review.objects.filter(status=Review.Status.APPROVED)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
