from django.db import models
from django.utils.text import slugify
from CheersMe.accounts.models import CustomUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class EventCategory(models.Model):
    CATEGORY_CHOICES = [
        ('band', 'Band'),
        ('concert', 'Concert'),
        ('party', 'Party'),
        ('business', 'Business'),
        ('wellness', 'Wellness'),
        ('lifestyle', 'Lifestyle'),
        ('food_offers', 'Food Offers'),
        ('drink_offers', 'Drink Offers'),
        ('brunch', 'Brunch'),
        ('games', 'Games'),
        ('quiz', 'Quiz'),
        ('karaoke', 'Karaoke'),
        ('market_day', 'Market Day'),
        ('holidays', 'Holidays'),
        ('spiritual', 'Spiritual'),
    ]
    
    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    icon = models.ImageField(upload_to='category_icons/', blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.get_name_display()
    
    class Meta:
        verbose_name_plural = 'Event Categories'
        ordering = ['name']

class Organizer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='organizer_profile')
    organization_name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='organizer_logos/', blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.organization_name

class Event(models.Model):
    EVENT_STATUS = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(EventCategory, on_delete=models.SET_NULL, null=True, related_name='events')
    
    # Images
    featured_image = models.ImageField(upload_to='event_images/')
    gallery = models.JSONField(default=list, blank=True)  # Store multiple image URLs
    
    # Location
    venue_name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Date and Time
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField()
    end_time = models.TimeField()
    
    # Pricing
    is_free = models.BooleanField(default=False)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Features
    has_food = models.BooleanField(default=False)
    food_deals = models.TextField(blank=True)
    has_drinks = models.BooleanField(default=False)
    drink_deals = models.TextField(blank=True)
    
    # Capacity
    total_capacity = models.PositiveIntegerField()
    remaining_capacity = models.PositiveIntegerField()
    
    # Status
    status = models.CharField(max_length=20, choices=EVENT_STATUS, default='draft')
    is_featured = models.BooleanField(default=False)
    
    # SEO
    meta_description = models.CharField(max_length=160, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Stats
    views = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.remaining_capacity is None:
            self.remaining_capacity = self.total_capacity
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    @property
    def is_sold_out(self):
        return self.remaining_capacity <= 0
    
    @property
    def sold_percentage(self):
        if self.total_capacity == 0:
            return 0
        return ((self.total_capacity - self.remaining_capacity) / self.total_capacity) * 100
    
    class Meta:
        ordering = ['-start_date', '-start_time']
        indexes = [
            models.Index(fields=['start_date', 'status']),
            models.Index(fields=['category', 'status']),
        ]

class EventFavorite(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='favorites')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'event')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.event.title}"

class EventReview(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    attended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'event')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.event.title} ({self.rating}★)"