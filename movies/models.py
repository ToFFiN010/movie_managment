import re
from django.db import models
from django.utils.text import slugify
from django.conf import settings

class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CastMember(models.Model):
    name = models.CharField(max_length=100)
    profile_image = models.ImageField(upload_to='cast/', blank=True, null=True)
    biography = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Movie(models.Model):
    class Status(models.TextChoices):
        UPCOMING = 'UPCOMING', 'Upcoming'
        NOW_SHOWING = 'NOW_SHOWING', 'Now Showing'
        ENDED = 'ENDED', 'Ended'
        ARCHIVED = 'ARCHIVED', 'Archived'

    class AgeCertification(models.TextChoices):
        U = 'U', 'U (Universal)'
        UA = 'U/A', 'U/A (Parental Guidance)'
        A_13 = '13+', '13+'
        A_16 = '16+', '16+'
        A_18 = '18+', '18+'

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    release_date = models.DateField()
    duration_minutes = models.PositiveIntegerField(help_text="Duration in minutes")
    age_certification = models.CharField(max_length=10, choices=AgeCertification.choices, default=AgeCertification.UA)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, related_name='movies')
    genres = models.ManyToManyField(Genre, related_name='movies')
    director = models.CharField(max_length=100)
    trailer_url = models.URLField(blank=True, null=True)
    youtube_video_id = models.CharField(max_length=50, blank=True, null=True)
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    backdrop_image = models.ImageField(upload_to='backdrops/', blank=True, null=True)
    tmdb_id = models.IntegerField(blank=True, null=True, help_text="The Movie Database ID")
    poster_path = models.CharField(max_length=255, blank=True, null=True, help_text="TMDB poster_path e.g. /qJ2tW6WMUDux911r6m7haRef0WH.jpg")
    backdrop_path = models.CharField(max_length=255, blank=True, null=True, help_text="TMDB backdrop_path e.g. /nMK28192i7WStCz2w34hZ1x8P7d.jpg")
    tmdb_poster_url = models.URLField(max_length=500, blank=True, null=True, help_text="Official TMDB Poster URL")
    tmdb_backdrop_url = models.URLField(max_length=500, blank=True, null=True, help_text="Official TMDB Backdrop URL")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOW_SHOWING)
    average_rating = models.FloatField(default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def get_poster_url(self):
        if self.poster_path:
            if self.poster_path.startswith('http://') or self.poster_path.startswith('https://') or self.poster_path.startswith('/media/') or self.poster_path.startswith('/static/'):
                return self.poster_path
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        if self.tmdb_poster_url:
            return self.tmdb_poster_url
        if self.poster:
            return self.poster.url
        return '/media/movies/posters/cineprime_default_fallback.png'

    @property
    def get_backdrop_url(self):
        if self.backdrop_path:
            if self.backdrop_path.startswith('http://') or self.backdrop_path.startswith('https://') or self.backdrop_path.startswith('/media/') or self.backdrop_path.startswith('/static/'):
                return self.backdrop_path
            return f"https://image.tmdb.org/t/p/w1280{self.backdrop_path}"
        if self.tmdb_backdrop_url:
            return self.tmdb_backdrop_url
        if self.backdrop_image:
            return self.backdrop_image.url
        return ''
        return self.get_poster_url

    class Meta:
        ordering = ['-release_date', 'title']
        indexes = [
            models.Index(fields=['status', '-release_date']),
            models.Index(fields=['slug']),
        ]

    def extract_youtube_id(self):
        if not self.trailer_url:
            return None
        # Valid youtube url formats:
        # youtube.com/watch?v=VIDEO_ID
        # youtu.be/VIDEO_ID
        # youtube.com/embed/VIDEO_ID
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.trailer_url)
            if match:
                return match.group(1)
        return None

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        video_id = self.extract_youtube_id()
        if video_id:
            self.youtube_video_id = video_id
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class MovieCast(models.Model):
    class Role(models.TextChoices):
        ACTOR = 'Actor', 'Actor'
        ACTRESS = 'Actress', 'Actress'
        DIRECTOR = 'Director', 'Director'
        PRODUCER = 'Producer', 'Producer'
        WRITER = 'Writer', 'Writer'
        MUSIC_DIRECTOR = 'Music Director', 'Music Director'
        CINEMATOGRAPHER = 'Cinematographer', 'Cinematographer'

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='cast_members')
    cast_member = models.ForeignKey(CastMember, on_delete=models.CASCADE, related_name='movie_roles')
    character_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.ACTOR)

    class Meta:
        verbose_name = 'Movie Cast'
        verbose_name_plural = 'Movie Casts'

    def __str__(self):
        return f"{self.cast_member.name} as {self.character_name or self.role} in {self.movie.title}"


class MovieImage(models.Model):
    class ImageType(models.TextChoices):
        POSTER = 'POSTER', 'Poster'
        BACKDROP = 'BACKDROP', 'Backdrop'
        SCREENSHOT = 'SCREENSHOT', 'Screenshot'
        GALLERY = 'GALLERY', 'Gallery'

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='movie_gallery/')
    image_type = models.CharField(max_length=20, choices=ImageType.choices, default=ImageType.GALLERY)
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.image_type} for {self.movie.title}"


class Watchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='watchlist')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='watchlist_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"
