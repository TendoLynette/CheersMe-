from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'organizer', 'start_date', 'status', 'available_tickets']
    list_filter = ['status', 'is_featured', 'start_date']
    search_fields = ['title', 'description', 'location']
    ordering = ['-start_date']
    readonly_fields = ['created_at', 'updated_at']