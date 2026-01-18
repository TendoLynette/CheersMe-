from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from CheersMe.events.models import Event, EventCategory, EventFavorite, EventReview
from CheersMe.tickets.models import Ticket, Order
from CheersMe.notifications.models import Notification
from django.contrib import messages
from math import radians, cos, sin, asin, sqrt

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km

@login_required
def home_view(request):
    # Get upcoming events
    today = timezone.now().date()
    upcoming_events = Event.objects.filter(
        status='published',
        start_date__gte=today
    ).select_related('category', 'organizer').order_by('start_date')[:10]
    
    # Get featured events
    featured_events = Event.objects.filter(
        status='published',
        is_featured=True,
        start_date__gte=today
    )[:5]
    
    # Get user's favorite events
    favorite_events = Event.objects.filter(
        favorited_by__user=request.user,
        status='published',
        start_date__gte=today
    ).order_by('start_date')[:5]
    
    # Get nearby events (if user has location)
    nearby_events = []
    if request.user.latitude and request.user.longitude:
        all_events = Event.objects.filter(
            status='published',
            start_date__gte=today
        )
        for event in all_events:
            distance = calculate_distance(
                request.user.latitude,
                request.user.longitude,
                float(event.latitude),
                float(event.longitude)
            )
            if distance <= 50:  # Within 50km
                event.distance = round(distance, 1)
                nearby_events.append(event)
        nearby_events = sorted(nearby_events, key=lambda x: x.distance)[:10]
    
    # Get categories
    categories = EventCategory.objects.all()
    
    # Get unread notifications count
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    context = {
        'upcoming_events': upcoming_events,
        'featured_events': featured_events,
        'favorite_events': favorite_events,
        'nearby_events': nearby_events,
        'categories': categories,
        'unread_notifications': unread_notifications,
    }
    
    return render(request, 'dashboard/home.html', context)

@login_required
def event_detail_view(request, slug):
    event = get_object_or_404(Event, slug=slug)
    
    # Increment view count
    event.views += 1
    event.save(update_fields=['views'])
    
    # Check if user has favorited this event
    is_favorited = EventFavorite.objects.filter(
        user=request.user,
        event=event
    ).exists()
    
    # Get user's review if exists
    user_review = EventReview.objects.filter(
        user=request.user,
        event=event
    ).first()
    
    # Get other reviews
    reviews = event.reviews.exclude(user=request.user).order_by('-created_at')[:5]
    
    # Check if user has tickets for this event
    has_tickets = Ticket.objects.filter(
        user=request.user,
        event=event
    ).exists()
    
    # Calculate distance if user has location
    distance = None
    if request.user.latitude and request.user.longitude:
        distance = calculate_distance(
            request.user.latitude,
            request.user.longitude,
            float(event.latitude),
            float(event.longitude)
        )
        distance = round(distance, 1)
    
    context = {
        'event': event,
        'is_favorited': is_favorited,
        'user_review': user_review,
        'reviews': reviews,
        'has_tickets': has_tickets,
        'distance': distance,
    }
    
    return render(request, 'dashboard/event_detail.html', context)

@login_required
def category_events_view(request, category_name):
    category = get_object_or_404(EventCategory, name=category_name)
    today = timezone.now().date()
    
    events = Event.objects.filter(
        category=category,
        status='published',
        start_date__gte=today
    ).order_by('start_date')
    
    context = {
        'category': category,
        'events': events,
    }
    
    return render(request, 'dashboard/category_events.html', context)

@login_required
def search_events_view(request):
    query = request.GET.get('q', '')
    today = timezone.now().date()
    
    events = Event.objects.filter(
        Q(title__icontains=query) | 
        Q(description__icontains=query) |
        Q(venue_name__icontains=query) |
        Q(city__icontains=query),
        status='published',
        start_date__gte=today
    ).order_by('start_date')
    
    context = {
        'events': events,
        'query': query,
    }
    
    return render(request, 'dashboard/search_results.html', context)

@login_required
def favorites_view(request):
    today = timezone.now().date()
    
    # Upcoming favorites
    upcoming_favorites = Event.objects.filter(
        favorited_by__user=request.user,
        status='published',
        start_date__gte=today
    ).order_by('start_date')
    
    # Past favorites
    past_favorites = Event.objects.filter(
        favorited_by__user=request.user,
        status='published',
        start_date__lt=today
    ).order_by('-start_date')
    
    context = {
        'upcoming_favorites': upcoming_favorites,
        'past_favorites': past_favorites,
    }
    
    return render(request, 'dashboard/favorites.html', context)

@login_required
def toggle_favorite_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    favorite, created = EventFavorite.objects.get_or_create(
        user=request.user,
        event=event
    )
    
    if not created:
        favorite.delete()
        messages.success(request, f'Removed {event.title} from favorites.')
    else:
        messages.success(request, f'Added {event.title} to favorites.')
    
    return redirect(request.META.get('HTTP_REFERER', 'dashboard:home'))

@login_required
def my_tickets_view(request):
    tickets = Ticket.objects.filter(
        user=request.user
    ).select_related('event', 'ticket_type', 'order').order_by('-created_at')
    
    context = {
        'tickets': tickets,
    }
    
    return render(request, 'dashboard/my_tickets.html', context)

@login_required
def ticket_detail_view(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    
    context = {
        'ticket': ticket,
    }
    
    return render(request, 'dashboard/ticket_detail.html', context)

@login_required
def my_orders_view(request):
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related('items', 'tickets').order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    
    return render(request, 'dashboard/my_orders.html', context)