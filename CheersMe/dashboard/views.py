from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from CheersMe.events.models import Event, EventCategory, EventFavorite, EventReview
from CheersMe.tickets.models import Ticket, Order
from CheersMe.notifications.models import Notification
from django.contrib import messages
from math import radians, cos, sin, asin, sqrt


# =========================
# HELPER FUNCTION
# =========================

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


# =========================
# HOME / DASHBOARD VIEW
# =========================

@login_required
def home(request):
    today = timezone.now().date()

    # Upcoming events
    upcoming_events = Event.objects.filter(
        status='published',
        start_date__gte=today
    ).select_related('category', 'organizer').order_by('start_date')[:10]

    # Featured events
    featured_events = Event.objects.filter(
        status='published',
        is_featured=True,
        start_date__gte=today
    )[:5]

    # Favorite events
    favorite_events = Event.objects.filter(
        favorited_by__user=request.user,
        status='published',
        start_date__gte=today
    ).order_by('start_date')[:5]

    # Nearby events
    nearby_events = []
    if hasattr(request.user, "latitude") and request.user.latitude and request.user.longitude:
        all_events = Event.objects.filter(
            status='published',
            start_date__gte=today
        )
        for event in all_events:
            if event.latitude and event.longitude:
                distance = calculate_distance(
                    request.user.latitude,
                    request.user.longitude,
                    float(event.latitude),
                    float(event.longitude)
                )
                if distance <= 50:
                    event.distance = round(distance, 1)
                    nearby_events.append(event)

        nearby_events = sorted(nearby_events, key=lambda x: x.distance)[:10]

    # Categories
    categories = EventCategory.objects.all()

    # =========================
    # RECOMMENDED EVENTS
    # =========================

    recommended_events = []

     #  Events user has favorited
    liked_event_ids = EventFavorite.objects.filter(
        user=request.user
        
    ).values_list("event_id", flat=True)
    fav_categories = EventCategory.objects.filter(
        events__id__in=liked_event_ids
    )

    # Categories from reviews
    reviewed_event_ids = EventReview.objects.filter(
        user=request.user
    ).values_list("event_id", flat=True)

    review_categories = EventCategory.objects.filter(
        events__id__in=reviewed_event_ids
    )

    # Categories from tickets bought
    ticket_event_ids = Ticket.objects.filter(
        user=request.user
    ).values_list("event_id", flat=True)

    ticket_categories = EventCategory.objects.filter(
        events__id__in=ticket_event_ids
    )

    liked_categories = (fav_categories | review_categories | ticket_categories).distinct()

    if liked_categories.exists():
        recommended_events = Event.objects.filter(
            category__in=liked_categories,
            status='published',
            start_date__gte=today
        ).exclude(
            id__in=liked_event_ids
        ).order_by('?')[:12]

    # Unread notifications
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
        'recommended_events': recommended_events,
        'unread_notifications': unread_notifications,
    }

    return render(request, 'dashboard/home.html', context)


# =========================
# EVENT DETAIL
# =========================

@login_required
def event_detail_view(request, slug):
    event = get_object_or_404(Event, slug=slug)

    event.views += 1
    event.save(update_fields=['views'])

    is_favorited = EventFavorite.objects.filter(
        user=request.user,
        event=event
    ).exists()

    user_review = EventReview.objects.filter(
        user=request.user,
        event=event
    ).first()

    reviews = event.reviews.exclude(user=request.user).order_by('-created_at')[:5]

    has_tickets = Ticket.objects.filter(
        user=request.user,
        event=event
    ).exists()

    distance = None
    if hasattr(request.user, "latitude") and request.user.latitude and request.user.longitude:
        if event.latitude and event.longitude:
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


# =========================
# CATEGORY EVENTS
# =========================

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


# =========================
# SEARCH
# =========================

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


# =========================
# FAVORITES
# =========================

@login_required
def favorites_view(request):
    today = timezone.now().date()

    upcoming_favorites = Event.objects.filter(
        favorited_by__user=request.user,
        status='published',
        start_date__gte=today
    ).order_by('start_date')

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


# =========================
# TOGGLE FAVORITE
# =========================

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


# =========================
# TICKETS & ORDERS
# =========================

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
