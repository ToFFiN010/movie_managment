import os
from PIL import Image
from django.contrib import admin
from django.conf import settings
from django.utils.html import format_html
from django.contrib import messages
from django.utils import timezone

from .models import Genre, Language, CastMember, Movie, MovieCast, MovieImage, MovieTrailer, Watchlist
from .services.tmdb import search_tmdb_movie

class MovieCastInline(admin.TabularInline):
    model = MovieCast
    extra = 1

class MovieImageInline(admin.TabularInline):
    model = MovieImage
    extra = 1

class MovieTrailerInline(admin.TabularInline):
    model = MovieTrailer
    extra = 1
    readonly_fields = ('verification_date', 'created_at', 'updated_at')

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

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'poster_thumbnail', 'poster_status_display', 'dimensions_and_size_display', 'release_date', 'status', 'average_rating', 'director')
    list_filter = ('status', 'release_date', 'language', 'genres', 'age_certification', 'country')
    search_fields = ('title', 'director', 'description', 'tmdb_id', 'cast_members__cast_member__name')

    prepopulated_fields = {'slug': ('title',)}
    inlines = [MovieCastInline, MovieImageInline, MovieTrailerInline]
    ordering = ('-release_date',)
    actions = ['validate_movie_images', 'repair_missing_posters', 'find_movies_missing_images', 'sync_selected_movies_with_tmdb']

    @admin.display(description="Poster")
    def poster_thumbnail(self, obj):
        url = obj.get_poster_url
        if url:
            return format_html('<img src="{}" style="width: 45px; height: 65px; object-fit: cover; border-radius: 4px;" />', url)
        return "-"

    @admin.display(description="Poster Status")
    def poster_status_display(self, obj):
        import os
        from django.conf import settings
        if not obj.poster or not obj.poster.name:
            return format_html('<span style="color: #EF4444; font-weight: bold;">MISSING</span>')
        abs_p = settings.MEDIA_ROOT / obj.poster.name
        if not abs_p.exists():
            return format_html('<span style="color: #EF4444; font-weight: bold;">FILE NOT FOUND</span>')
        if abs_p.stat().st_size == 0:
            return format_html('<span style="color: #F59E0B; font-weight: bold;">EMPTY FILE</span>')
        if 'placeholder' in obj.poster.name.lower():
            return format_html('<span style="color: #3B82F6; font-weight: bold;">PLACEHOLDER</span>')
        return format_html('<span style="color: #10B981; font-weight: bold;">VALID</span>')

    @admin.display(description="Dimensions & Size")
    def dimensions_and_size_display(self, obj):
        import os
        from PIL import Image
        from django.conf import settings
        if not obj.poster or not obj.poster.name:
            return "-"
        abs_p = settings.MEDIA_ROOT / obj.poster.name
        if not abs_p.exists():
            return "-"
        try:
            kb = round(abs_p.stat().st_size / 1024, 1)
            with Image.open(abs_p) as im:
                w, h = im.size
            return f"{w}x{h} ({kb}KB)"
        except Exception:
            return "-"

    @admin.action(description="Validate Selected Movie Images")
    def validate_movie_images(self, request, queryset):
        import os
        from PIL import Image
        from django.conf import settings
        valid_cnt = 0
        invalid_cnt = 0
        for movie in queryset:
            if movie.poster and movie.poster.name:
                abs_p = settings.MEDIA_ROOT / movie.poster.name
                if abs_p.exists() and abs_p.stat().st_size > 0:
                    try:
                        with Image.open(abs_p) as im:
                            im.verify()
                        valid_cnt += 1
                        continue
                    except Exception:
                        pass
            invalid_cnt += 1
        self.message_user(request, f"Image Validation Complete: {valid_cnt} valid posters, {invalid_cnt} invalid/missing posters.", level=messages.INFO)

    @admin.action(description="Repair Missing Posters (TMDb / Fallback)")
    def repair_missing_posters(self, request, queryset):
        from movies.management.commands.repair_movie_images import Command as RepairCmd
        cmd = RepairCmd()
        cmd.handle(force=True)
        self.message_user(request, f"Completed poster repair for {queryset.count()} movies.", level=messages.SUCCESS)

    @admin.action(description="Find Movies Missing Images")
    def find_movies_missing_images(self, request, queryset):
        missing = [m.title for m in queryset if not m.poster or not (settings.MEDIA_ROOT / m.poster.name).exists()]
        if missing:
            self.message_user(request, f"Movies missing valid posters ({len(missing)}): {', '.join(missing[:10])}", level=messages.WARNING)
        else:
            self.message_user(request, "All selected movies have valid poster images!", level=messages.SUCCESS)

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
    list_display = ('movie', 'image_preview', 'image_type', 'verification_status', 'image_status', 'source_name', 'verification_date')
    list_filter = ('verification_status', 'image_status', 'image_type', 'is_primary', 'source_name')
    search_fields = ('movie__title', 'source_name', 'caption')
    readonly_fields = ('verification_date', 'uploaded_at')

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 45px; height: 65px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "-"

@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'created_at')
    search_fields = ('user__username', 'movie__title')

@admin.register(MovieTrailer)
class MovieTrailerAdmin(admin.ModelAdmin):
    list_display = ('movie', 'trailer_preview', 'video_id', 'channel_name', 'trailer_type', 'confidence_score', 'verification_status', 'is_primary', 'verification_date')
    list_filter = ('verification_status', 'trailer_type', 'is_primary', 'trailer_source')
    search_fields = ('movie__title', 'video_title', 'channel_name', 'video_id')
    readonly_fields = ('verification_date', 'created_at', 'updated_at')
    actions = ['set_as_primary_trailer', 'verify_selected_trailers', 'revalidate_youtube_status']

    @admin.display(description="Trailer Preview")
    def trailer_preview(self, obj):
        if obj.video_id and obj.video_id != 'NO_TRAILER':
            thumb = obj.thumbnail_url or f"https://img.youtube.com/vi/{obj.video_id}/hqdefault.jpg"
            return format_html(
                '<div style="display: flex; align-items: center; gap: 8px;">'
                '<img src="{}" style="width: 70px; height: 42px; object-fit: cover; border-radius: 4px;" />'
                '<div><a href="https://www.youtube.com/watch?v={}" target="_blank" style="color: #3B82F6; font-weight: bold;">{}</a><br/><small style="color: #9CA3AF;">{}</small></div>'
                '</div>',
                thumb, obj.video_id, obj.video_title[:35], obj.channel_name
            )
        return "-"

    @admin.action(description="Set Selected Trailer as Primary")
    def set_as_primary_trailer(self, request, queryset):
        cnt = 0
        for tr in queryset:
            tr.is_primary = True
            tr.save()
            cnt += 1
        self.message_user(request, f"Updated {cnt} trailers as primary official trailers.", level=messages.SUCCESS)

    @admin.action(description="Verify Selected Trailers")
    def verify_selected_trailers(self, request, queryset):
        cnt = queryset.update(verification_status=MovieTrailer.VerificationStatus.VERIFIED, verification_date=timezone.now())
        self.message_user(request, f"Verified {cnt} trailers.", level=messages.SUCCESS)

    @admin.action(description="Re-validate YouTube Status")
    def revalidate_youtube_status(self, request, queryset):
        from movies.management.commands.validate_movie_trailers import Command as ValidateCmd
        v_cmd = ValidateCmd()
        valid = 0
        broken = 0
        for tr in queryset:
            st, reason = v_cmd.verify_trailer_instance(tr)
            if st == 'VALID': valid += 1
            else: broken += 1
        self.message_user(request, f"Validation complete: {valid} valid, {broken} broken/unavailable.", level=messages.INFO)

