from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL

class Ticket(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    price = models.DecimalField(max_digits=8, decimal_places=2)
    purchased_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} - {self.event}"
