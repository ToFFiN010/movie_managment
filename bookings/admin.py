from django.contrib import admin
from .models import ShowSchedule, Booking, BookingSeat, Payment

class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    readonly_fields = ('seat', 'price')

class PaymentInline(admin.StackedInline):
    model = Payment
    can_delete = False
    readonly_fields = ('transaction_id', 'payment_method', 'amount', 'payment_status', 'created_at')

@admin.register(ShowSchedule)
class ShowScheduleAdmin(admin.ModelAdmin):
    list_display = ('movie', 'theater', 'screen', 'show_date', 'start_time', 'end_time', 'ticket_price', 'status')
    list_filter = ('status', 'show_date', 'theater', 'screen__screen_type')
    search_fields = ('movie__title', 'theater__name', 'screen__name')
    date_hierarchy = 'show_date'

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'user', 'show', 'total_amount', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('booking_reference', 'user__username', 'user__email', 'show__movie__title')
    inlines = [BookingSeatInline, PaymentInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'booking', 'payment_method', 'amount', 'payment_status', 'created_at')
    list_filter = ('payment_method', 'payment_status')
    search_fields = ('transaction_id', 'booking__booking_reference', 'booking__user__username')
