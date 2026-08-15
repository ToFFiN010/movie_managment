from rest_framework import serializers
from .models import Movie, Genre, Language, CastMember, MovieCast, MovieImage
from theaters.models import Theater, Screen, Seat
from bookings.models import ShowSchedule, Booking, BookingSeat
from reviews.models import Review

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = '__all__'

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'

class CastMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CastMember
        fields = '__all__'

class MovieImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieImage
        fields = '__all__'

class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    language = LanguageSerializer(read_only=True)
    images = MovieImageSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = '__all__'

class TheaterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theater
        fields = '__all__'

class ShowScheduleSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    theater_name = serializers.CharField(source='theater.name', read_only=True)
    screen_name = serializers.CharField(source='screen.name', read_only=True)

    class Meta:
        model = ShowSchedule
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='show.movie.title', read_only=True)
    theater_name = serializers.CharField(source='show.theater.name', read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = '__all__'
