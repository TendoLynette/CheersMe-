from django.contrib import admin
from .models import EventCategory, Organizer, Event, EventFavorite, EventReview

@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ['organization_name', 'user', 'verified', 'rating', 'created_at']
    list_filter = ['verified', 'created_at']
    search_fields = ['organization_name', 'user__email']
    readonly_fields = ['created_at']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'organizer', 'category', 'start_date', 'status', 'is_featured', 'remaining_capacity']
    list_filter = ['status', 'is_featured', 'category', 'start_date']
    search_fields = ['title', 'description', 'venue_name', 'city']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'views']

    # ✅ IMPORTANT — EXCLUDE gallery
    exclude = ['gallery']

    fieldsets = (
        ('Basic Information', {
            'fields': ('organizer', 'title', 'slug', 'description', 'category', 'status', 'is_featured')
        }),
        ('Media', {
            'fields': ('featured_image',)
        }),
        ('Location', {
            'fields': ('venue_name', 'address', 'city', 'latitude', 'longitude')
        }),
        ('Date & Time', {
            'fields': ('start_date', 'start_time', 'end_date', 'end_time')
        }),
        ('Pricing', {
            'fields': ('is_free', 'base_price')
        }),
        ('Features', {
            'fields': ('has_food', 'food_deals', 'has_drinks', 'drink_deals')
        }),
        ('Capacity', {
            'fields': ('total_capacity', 'remaining_capacity')
        }),
        ('Statistics', {
            'fields': ('views', 'created_at', 'updated_at')
        }),
    )

@admin.register(EventFavorite)
class EventFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'event__title']

@admin.register(EventReview)
class EventReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'rating', 'attended', 'created_at']
    list_filter = ['rating', 'attended', 'created_at']
    search_fields = ['user__email', 'event__title', 'comment']

