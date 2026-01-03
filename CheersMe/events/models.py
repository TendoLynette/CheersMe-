from django.db import models
from CheersMe.accounts.models import CustomUser
import uuid

class Event(models.Model):
    EVENT_STATUS = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Event details
    organizer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='organized_events')
    location = models.CharField(max_length=300)
    venue_name = models.CharField(max_length=200, blank=True)
    
    # Date and time
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Ticketing
    total_tickets = models.PositiveIntegerField()
    available_tickets = models.PositiveIntegerField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status and visibility
    status = models.CharField(max_length=20, choices=EVENT_STATUS, default='draft')
    is_featured = models.BooleanField(default=False)
    
    # Media
    cover_image = models.ImageField(upload_to='event_covers/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['organizer']),
        ]