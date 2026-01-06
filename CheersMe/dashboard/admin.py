from django.contrib import admin
from .models import DashboardStats

@admin.register(DashboardStats)
class DashboardStatsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "total_events_attended",
        "total_tickets_bought",
        "last_activity",
    )
