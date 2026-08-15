from django.contrib import admin
from .models import Genre, Language, CastMember, Movie, MovieCast, MovieImage, Watchlist

class MovieCastInline(admin.TabularInline):
    model = MovieCast
    extra = 1

class MovieImageInline(admin.TabularInline):
    model = MovieImage
    extra = 1

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(CastMember)
class CastMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'date_of_birth', 'created_at')
    search_fields = ('name',)

from django.utils.html import format_html
from django.contrib import messages
from .services.tmdb import search_tmdb_movie

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'poster_thumbnail', 'tmdb_id', 'poster_path', 'release_date', 'average_rating', 'status')
    list_filter = ('status', 'language', 'genres', 'age_certification')
    search_fields = ('title', 'director', 'description', 'tmdb_id')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [MovieCastInline, MovieImageInline]
    ordering = ('-release_date',)
    actions = ['sync_selected_movies_with_tmdb']

    @admin.display(description="Poster")
    def poster_thumbnail(self, obj):
        url = obj.get_poster_url
        if url:
            return format_html('<img src="{}" style="width: 45px; height: 65px; object-fit: cover; border-radius: 4px;" />', url)
        return "-"

    @admin.action(description="Sync Selected Movies with TMDB")
    def sync_selected_movies_with_tmdb(self, request, queryset):
        success_count = 0
        fail_count = 0

        for movie in queryset:
            year = movie.release_date.year if movie.release_date else None
            tmdb_data = search_tmdb_movie(movie.title, release_year=year)

            if tmdb_data and tmdb_data.get('poster_path'):
                movie.tmdb_id = tmdb_data.get('tmdb_id')
                movie.poster_path = tmdb_data.get('poster_path')
                movie.backdrop_path = tmdb_data.get('backdrop_path')
                movie.tmdb_poster_url = tmdb_data.get('poster_url')
                movie.tmdb_backdrop_url = tmdb_data.get('backdrop_url')
                if tmdb_data.get('vote_average'):
                    movie.average_rating = round(float(tmdb_data['vote_average']), 1)
                movie.save()
                success_count += 1
                self.message_user(request, f"✓ {movie.title} → synced (poster_path: {movie.poster_path})", level=messages.SUCCESS)
            else:
                fail_count += 1
                self.message_user(request, f"⚠ Could not confidently match TMDB for: {movie.title}", level=messages.WARNING)

        self.message_user(request, f"Completed TMDB Sync: {success_count} synced successfully, {fail_count} unassigned.", level=messages.INFO)

@admin.register(MovieCast)
class MovieCastAdmin(admin.ModelAdmin):
    list_display = ('movie', 'cast_member', 'character_name', 'role')
    list_filter = ('role',)
    search_fields = ('movie__title', 'cast_member__name', 'character_name')

@admin.register(MovieImage)
class MovieImageAdmin(admin.ModelAdmin):
    list_display = ('movie', 'image_type', 'is_primary', 'uploaded_at')
    list_filter = ('image_type', 'is_primary')

@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'created_at')
    search_fields = ('user__username', 'movie__title')
