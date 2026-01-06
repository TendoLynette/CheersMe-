from django.contrib import admin
from .models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "price", "purchased_at", "is_used")
    list_filter = ("is_used", "purchased_at")
    search_fields = ("user__username", "event__title")
