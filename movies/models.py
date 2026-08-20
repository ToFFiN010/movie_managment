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
        RELEASED = 'RELEASED', 'Released'
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
    country = models.CharField(max_length=100, default='United States', blank=True)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, related_name='movies')
    genres = models.ManyToManyField(Genre, related_name='movies')
    director = models.CharField(max_length=100)
    trailer_url = models.URLField(blank=True, null=True)
    youtube_video_id = models.CharField(max_length=50, blank=True, null=True)
    trailer_title = models.CharField(max_length=255, blank=True, null=True)
    trailer_source = models.CharField(max_length=50, default='YouTube', blank=True)
    trailer_type = models.CharField(max_length=40, default='OFFICIAL_TRAILER', blank=True)
    trailer_verified = models.BooleanField(default=False)
    trailer_verified_at = models.DateTimeField(null=True, blank=True)
    trailer_thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    poster = models.ImageField(upload_to='movies/posters/', blank=True, null=True)
    backdrop_image = models.ImageField(upload_to='backdrops/', blank=True, null=True)
    poster_source = models.CharField(max_length=50, default='unknown', blank=True)
    poster_source_url = models.URLField(max_length=500, blank=True, null=True)
    poster_source_id = models.CharField(max_length=100, blank=True, null=True)
    poster_verified = models.BooleanField(default=False)
    poster_last_checked = models.DateTimeField(null=True, blank=True)
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

    media_status = models.CharField(max_length=40, default='ok', choices=[('ok', 'OK'), ('manual_review', 'Manual Review'), ('missing_poster', 'Missing Poster'), ('missing_trailer', 'Missing Trailer')], blank=True)
    image_source = models.CharField(max_length=50, default='TMDB', blank=True)
    image_source_id = models.CharField(max_length=100, blank=True, null=True)
    image_source_url = models.URLField(max_length=500, blank=True, null=True)

    @property
    def has_active_shows(self):
        return self.shows.filter(status__in=['OPEN', 'UPCOMING']).exists()

    @property
    def primary_trailer(self):
        tr = self.trailers.filter(is_primary=True).first()
        if tr:
            return tr
        return self.trailers.filter(verification_status='VERIFIED').first()

    @property
    def release_year(self):
        return self.release_date.year if self.release_date else 2026

    @property
    def get_poster_url(self):
        import os
        from django.conf import settings
        ts = f"?v={int(self.updated_at.timestamp())}" if self.updated_at else ""

        # Priority A: Local uploaded poster (must exist, >1KB, non-placeholder)
        if self.poster and self.poster.name:
            if getattr(self, 'poster_source', '') != 'placeholder' and not self.poster.name.endswith('_fallback.jpg'):
                try:
                    if os.path.exists(self.poster.path) and os.path.getsize(self.poster.path) > 1000:
                        return f"{self.poster.url}{ts}"
                except Exception:
                    pass

        # Priority B: Valid external poster URL or TMDB path
        if self.poster_source_url and (self.poster_source_url.startswith('http://') or self.poster_source_url.startswith('https://')):
            return self.poster_source_url

        if self.tmdb_poster_url and (self.tmdb_poster_url.startswith('http://') or self.tmdb_poster_url.startswith('https://')):
            return self.tmdb_poster_url

        if self.poster_path:
            if self.poster_path.startswith('http://') or self.poster_path.startswith('https://'):
                return self.poster_path
            elif self.poster_path.startswith('/media/') or self.poster_path.startswith('/static/'):
                return self.poster_path
            elif not self.poster_path.startswith('/media/movies/'):
                return f"https://image.tmdb.org/t/p/w500{self.poster_path if self.poster_path.startswith('/') else '/' + self.poster_path}"

        # Priority C: Cached/processed poster files on disk
        media_root = settings.MEDIA_ROOT
        slug = self.slug or f"movie-{self.id}"
        candidates = [
            f"movies/posters/movie_{self.id}_poster.webp",
            f"movies/posters/movie_{self.id}_poster.jpg",
            f"movies/posters/{slug}-poster.webp",
            f"movies/posters/{slug}-poster.jpg",
            f"movies/posters/{slug}.webp",
            f"movies/posters/{slug}.jpg",
        ]
        for rel_cand in candidates:
            abs_cand = media_root / rel_cand
            if abs_cand.exists() and abs_cand.stat().st_size > 1000:
                return f"{settings.MEDIA_URL}{rel_cand}{ts}"

        # Priority D: Safe fallback placeholder
        return f'{settings.MEDIA_URL}movies/posters/cineprime_default_fallback.png{ts}'

    @property
    def get_backdrop_url(self):
        import os
        from django.conf import settings
        if self.backdrop_image and self.backdrop_image.name:
            try:
                if os.path.exists(self.backdrop_image.path) and os.path.getsize(self.backdrop_image.path) > 1000:
                    return self.backdrop_image.url
            except Exception:
                pass
        if self.backdrop_path:
            if self.backdrop_path.startswith('http://') or self.backdrop_path.startswith('https://') or self.backdrop_path.startswith('/media/') or self.backdrop_path.startswith('/static/'):
                return self.backdrop_path
            return f"https://image.tmdb.org/t/p/w1280{self.backdrop_path}"
        if self.tmdb_backdrop_url:
            return self.tmdb_backdrop_url
        return self.get_poster_url



    class Meta:
        ordering = ['-release_date', 'title']
        indexes = [
            models.Index(fields=['status', '-release_date']),
            models.Index(fields=['slug']),
            models.Index(fields=['-release_date']),
            models.Index(fields=['-average_rating']),
            models.Index(fields=['title']),
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
            base_slug = slugify(self.title) or 'movie'
            slug = base_slug
            counter = 1
            qs = Movie.objects.all()
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        video_id = self.extract_youtube_id()
        if video_id:
            self.youtube_video_id = video_id

        # Automatic status calculation based on release_date
        if self.release_date:
            from datetime import date
            if self.release_date > date.today() and self.status not in [self.Status.ENDED, self.Status.ARCHIVED]:
                self.status = self.Status.UPCOMING
            elif self.release_date <= date.today() and self.status == self.Status.UPCOMING:
                self.status = self.Status.NOW_SHOWING

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

    class VerificationStatus(models.TextChoices):
        VERIFIED = 'VERIFIED', 'Verified'
        PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review'
        COPYRIGHT_REVIEW = 'COPYRIGHT_REVIEW', 'Copyright Review Required'
        AMBIGUOUS = 'AMBIGUOUS', 'Ambiguous Match'
        FAILED = 'FAILED', 'Failed'
        PLACEHOLDER = 'PLACEHOLDER', 'Placeholder'

    class ImageStatus(models.TextChoices):
        VALID = 'VALID', 'Valid'
        MISSING = 'MISSING', 'Missing'
        BROKEN = 'BROKEN', 'Broken'
        DUPLICATE = 'DUPLICATE', 'Duplicate Image'
        SUSPECTED_WRONG_IMAGE = 'SUSPECTED_WRONG_IMAGE', 'Suspected Wrong Image'

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='movie_gallery/')
    image_type = models.CharField(max_length=20, choices=ImageType.choices, default=ImageType.GALLERY)
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    source_name = models.CharField(max_length=100, default='Promotional Archive', blank=True)
    source_url = models.CharField(max_length=500, blank=True)
    license_information = models.CharField(max_length=200, default='Promotional / Fair Use', blank=True)
    verification_status = models.CharField(max_length=30, choices=VerificationStatus.choices, default=VerificationStatus.VERIFIED)
    image_status = models.CharField(max_length=30, choices=ImageStatus.choices, default=ImageStatus.VALID)
    verification_date = models.DateTimeField(null=True, blank=True)
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


class RecentlyViewedMovie(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recently_viewed_movies')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='recently_viewed_by')
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        unique_together = ('user', 'movie')
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
        ]

    def __str__(self):
        return f"{self.user.username} viewed {self.movie.title}"


class MovieTrailer(models.Model):
    class TrailerType(models.TextChoices):
        OFFICIAL_TRAILER = 'OFFICIAL_TRAILER', 'Official Trailer'
        OFFICIAL_TEASER = 'OFFICIAL_TEASER', 'Official Teaser'
        FINAL_TRAILER = 'FINAL_TRAILER', 'Final Trailer'
        INTERNATIONAL_TRAILER = 'INTERNATIONAL_TRAILER', 'International Trailer'
        TV_SPOT = 'TV_SPOT', 'TV Spot'
        CLIP = 'CLIP', 'Official Clip'
        BEHIND_THE_SCENES = 'BEHIND_THE_SCENES', 'Behind The Scenes'
        INTERVIEW = 'INTERVIEW', 'Interview'
        FEATURETTE = 'FEATURETTE', 'Featurette'

    class VerificationStatus(models.TextChoices):
        VERIFIED = 'VERIFIED', 'Verified'
        PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review'
        MANUAL_REVIEW_REQUIRED = 'MANUAL_REVIEW_REQUIRED', 'Manual Review Required'
        NO_TRAILER_FOUND = 'NO_TRAILER_FOUND', 'No Trailer Found'
        MULTIPLE_MATCHES = 'MULTIPLE_MATCHES', 'Multiple Matches'
        TRAILER_UNAVAILABLE = 'TRAILER_UNAVAILABLE', 'Trailer Unavailable'
        TRAILER_BROKEN = 'TRAILER_BROKEN', 'Trailer Broken'
        REJECTED = 'REJECTED', 'Rejected'

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='trailers')
    trailer_url = models.URLField(max_length=500)
    video_id = models.CharField(max_length=50)
    video_title = models.CharField(max_length=255)
    channel_name = models.CharField(max_length=150, blank=True)
    channel_id = models.CharField(max_length=100, blank=True)
    trailer_source = models.CharField(max_length=50, default='YouTube')
    trailer_type = models.CharField(max_length=40, choices=TrailerType.choices, default=TrailerType.OFFICIAL_TRAILER)
    is_primary = models.BooleanField(default=False)
    confidence_score = models.PositiveIntegerField(default=0)
    verification_status = models.CharField(max_length=40, choices=VerificationStatus.choices, default=VerificationStatus.PENDING_REVIEW)
    verification_date = models.DateTimeField(null=True, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    notes_or_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', '-confidence_score', '-created_at']
        indexes = [
            models.Index(fields=['movie', 'is_primary']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['video_id']),
        ]

    def extract_video_id(self):
        if not self.trailer_url:
            return self.video_id
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.trailer_url)
            if match:
                return match.group(1)
        return self.video_id

    def save(self, *args, **kwargs):
        vid = self.extract_video_id()
        if vid:
            self.video_id = vid
            if not self.trailer_url or 'embed' in self.trailer_url:
                self.trailer_url = f"https://www.youtube.com/watch?v={vid}"

        from django.utils import timezone
        if self.verification_status == self.VerificationStatus.VERIFIED and not self.verification_date:
            self.verification_date = timezone.now()

        # Enforce single primary trailer per movie
        if self.is_primary:
            MovieTrailer.objects.filter(movie=self.movie, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
            
            # Sync back onto parent Movie model instance
            m = self.movie
            m.trailer_url = self.trailer_url
            m.youtube_video_id = self.video_id
            m.trailer_title = self.video_title
            m.trailer_source = self.trailer_source
            m.trailer_type = self.trailer_type
            m.trailer_verified = (self.verification_status == self.VerificationStatus.VERIFIED)
            m.trailer_verified_at = self.verification_date
            m.trailer_thumbnail_url = self.thumbnail_url or f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg"
            m.save(update_fields=['trailer_url', 'youtube_video_id', 'trailer_title', 'trailer_source', 'trailer_type', 'trailer_verified', 'trailer_verified_at', 'trailer_thumbnail_url'])

        super().save(*args, **kwargs)

    def __str__(self):
        primary_str = " (Primary)" if self.is_primary else ""
        return f"{self.get_trailer_type_display()} for {self.movie.title}{primary_str}"


