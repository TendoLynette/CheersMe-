from django.db import models
from CheersMe.accounts.models import CustomUser 
from CheersMe.events.models import Event  # Add this line
import uuid

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('welcome', 'Welcome'),
        ('event_reminder', 'Event Reminder'),
        ('ticket_purchased', 'Ticket Purchased'),
        ('event_update', 'Event Update'),
        ('event_cancelled', 'Event Cancelled'),
        ('favorite_event', 'Favorite Event Update'),
        ('review_request', 'Review Request'),
        ('promotional', 'Promotional'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    # Optional related objects
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    link = models.URLField(blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    sent_via_email = models.BooleanField(default=False)
    sent_via_push = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]

class EmailTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('welcome', 'Welcome Email'),
        ('ticket_confirmation', 'Ticket Confirmation'),
        ('event_reminder', 'Event Reminder'),
        ('password_reset', 'Password Reset'),
        ('event_cancelled', 'Event Cancelled'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES, unique=True)
    subject = models.CharField(max_length=200)
    html_content = models.TextField()
    text_content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']