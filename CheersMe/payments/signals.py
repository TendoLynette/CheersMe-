from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from CheersMe.dashboard.models import DashboardStats

@receiver(post_save, sender=Payment)
def update_dashboard_on_payment(sender, instance, created, **kwargs):
    if instance.status == "completed":
        dashboard = instance.user.dashboard_stats
        dashboard.total_tickets_bought += 1
        dashboard.save()
