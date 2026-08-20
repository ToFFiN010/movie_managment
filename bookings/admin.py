from django.contrib import admin
from .models import ShowSchedule, Booking, BookingSeat, Payment, Reservation, ReservationSeat, Coupon, Refund

class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    readonly_fields = ('seat', 'price')

class PaymentInline(admin.StackedInline):
    model = Payment
    can_delete = False
    extra = 0
    readonly_fields = ('gateway', 'gateway_order_id', 'transaction_id', 'payment_method', 'amount', 'currency', 'payment_status', 'signature', 'failure_reason', 'webhook_verified', 'created_at', 'updated_at')

@admin.register(ShowSchedule)
class ShowScheduleAdmin(admin.ModelAdmin):
    list_display = ('movie', 'theater', 'screen', 'show_date', 'start_time', 'end_time', 'ticket_price', 'status')
    list_filter = ('status', 'show_date', 'theater', 'screen__screen_type', 'movie')
    search_fields = ('movie__title', 'theater__name', 'screen__name')
    date_hierarchy = 'show_date'
    actions = ['activate_selected_showtimes', 'cancel_selected_showtimes', 'mark_completed_showtimes']

    @admin.action(description="Activate / Open Selected Showtimes")
    def activate_selected_showtimes(self, request, queryset):
        updated = queryset.update(status=ShowSchedule.Status.OPEN)
        self.message_user(request, f"Activated {updated} selected showtimes.")

    @admin.action(description="Cancel Selected Showtimes")
    def cancel_selected_showtimes(self, request, queryset):
        updated = queryset.update(status=ShowSchedule.Status.CANCELLED)
        self.message_user(request, f"Cancelled {updated} selected showtimes.")

    @admin.action(description="Mark Selected Showtimes as Completed / Closed")
    def mark_completed_showtimes(self, request, queryset):
        updated = queryset.update(status=ShowSchedule.Status.CLOSED)
        self.message_user(request, f"Marked {updated} selected showtimes as completed.")

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'user', 'show', 'seats_summary', 'total_amount', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'show__movie')
    search_fields = ('booking_reference', 'user__username', 'user__email', 'show__movie__title', 'show__theater__name')
    readonly_fields = ('booking_reference', 'created_at')
    inlines = [BookingSeatInline, PaymentInline]

    def seats_summary(self, obj):
        return ", ".join([bs.seat.label for bs in obj.booked_seats.all()])
    seats_summary.short_description = 'Seats'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'gateway_order_id', 'booking', 'get_user', 'amount', 'currency', 'payment_status', 'gateway', 'webhook_verified', 'created_at')
    list_filter = ('gateway', 'payment_status', 'webhook_verified', 'created_at')
    search_fields = ('transaction_id', 'gateway_order_id', 'booking__booking_reference', 'booking__user__username', 'booking__user__email')
    readonly_fields = ('gateway_order_id', 'transaction_id', 'signature', 'created_at', 'updated_at')

    def get_user(self, obj):
        return obj.booking.user.username
    get_user.short_description = 'User'

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation_id', 'user', 'show', 'status', 'total_amount', 'created_at', 'expires_at')
    list_filter = ('status', 'created_at')
    search_fields = ('reservation_id', 'user__username', 'show__movie__title')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_booking_amount', 'is_active', 'valid_from', 'valid_to')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code',)

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('refund_transaction_id', 'booking', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('refund_transaction_id', 'booking__booking_reference')
