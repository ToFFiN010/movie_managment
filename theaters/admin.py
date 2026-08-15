from django.contrib import admin
from .models import Theater, Screen, Seat

class ScreenInline(admin.TabularInline):
    model = Screen
    extra = 1

class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0

@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'location', 'phone', 'status', 'created_at')
    list_filter = ('status', 'city')
    search_fields = ('name', 'city', 'location', 'address')
    inlines = [ScreenInline]

@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ('name', 'theater', 'screen_number', 'capacity', 'screen_type')
    list_filter = ('screen_type', 'theater__city')
    search_fields = ('name', 'theater__name')
    inlines = [SeatInline]

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('screen', 'row', 'seat_number', 'seat_type', 'price_multiplier', 'is_active')
    list_filter = ('seat_type', 'is_active', 'screen__theater')
    search_fields = ('screen__theater__name', 'screen__name', 'row')
