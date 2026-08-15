from django.contrib import admin
from .models import Review, ReviewReport

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating', 'is_verified_viewer', 'status', 'report_count', 'created_at')
    list_filter = ('status', 'rating', 'is_verified_viewer')
    search_fields = ('user__username', 'movie__title', 'review_text')
    actions = ['approve_reviews', 'reject_reviews', 'hide_reviews']

    @admin.action(description='Approve selected reviews')
    def approve_reviews(self, request, queryset):
        for review in queryset:
            review.status = Review.Status.APPROVED
            review.save()

    @admin.action(description='Reject selected reviews')
    def reject_reviews(self, request, queryset):
        for review in queryset:
            review.status = Review.Status.REJECTED
            review.save()

    @admin.action(description='Hide selected reviews')
    def hide_reviews(self, request, queryset):
        for review in queryset:
            review.status = Review.Status.HIDDEN
            review.save()

@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ('review', 'reported_by', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status')
    search_fields = ('review__movie__title', 'reported_by__username', 'description')
    actions = ['mark_resolved', 'hide_associated_review']

    @admin.action(description='Mark report as resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(status=ReviewReport.Status.RESOLVED)

    @admin.action(description='Hide associated review and resolve report')
    def hide_associated_review(self, request, queryset):
        for report in queryset:
            report.review.status = Review.Status.HIDDEN
            report.review.save()
            report.status = ReviewReport.Status.RESOLVED
            report.save()
