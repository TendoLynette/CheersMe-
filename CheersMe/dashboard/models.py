from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL

class DashboardStats(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="dashboard_stats"
    )
    total_events_attended = models.PositiveIntegerField(default=0)
    total_tickets_bought = models.PositiveIntegerField(default=0)
    favorite_category = models.CharField(max_length=100, blank=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dashboard stats for {self.user}"
