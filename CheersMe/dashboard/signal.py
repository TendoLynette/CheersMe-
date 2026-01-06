from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DashboardStats

User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=User)
def create_dashboard_stats(sender, instance, created, **kwargs):
    if created:
        DashboardStats.objects.create(user=instance)
