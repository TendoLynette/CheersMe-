from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
import json

from .models import Event, EventCategory, Organizer, EventFavorite, EventReview
from .forms import EventForm, EventReviewForm
from CheersMe.tickets.models import Ticket


# ====================================
# UTILITY FUNCTIONS
# ====================================

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula
    Returns distance in kilometers
    """
    # Convert to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def annotate_event_stats(queryset):
    """
    Annotate events with useful statistics
    """
    return queryset.annotate(
        favorites_count=Count('favorited_by', distinct=True),
        reviews_count=Count('reviews', distinct=True),
        average_rating=Avg('reviews__rating'),
        tickets_sold=Count('tickets', distinct=True)
    )


# ====================================
# PUBLIC EVENT VIEWS
# ====================================

def events_list_view(request):
    """
    Display list of all published events with filtering and pagination
    """
    today = timezone.now().date()
    
    # Base queryset - only published future events
    events = Event.objects.filter(
        status='published',
        start_date__gte=today
    ).select_related('category', 'organizer').order_by('start_date', 'start_time')
    
    # Apply filters
    category = request.GET.get('category')
    city = request.GET.get('city')
    date = request.GET.get('date')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    is_free = request.GET.get('is_free')
    has_food = request.GET.get('has_food')
    has_drinks = request.GET.get('has_drinks')
    
    if category:
        events = events.filter(category__name=category)
    
    if city:
        events = events.filter(city__icontains=city)
    
    if date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            events = events.filter(start_date=date_obj)
        except ValueError:
            pass
    
    if price_min:
        try:
            events = events.filter(base_price__gte=float(price_min))
        except ValueError:
            pass
    
    if price_max:
        try:
            events = events.filter(base_price__lte=float(price_max))
        except ValueError:
            pass
    
    if is_free == 'true':
        events = events.filter(is_free=True)
    
    if has_food == 'true':
        events = events.filter(has_food=True)
    
    if has_drinks == 'true':
        events = events.filter(has_drinks=True)
    
    # Annotate with stats
    events = annotate_event_stats(events)
    
    # Pagination
    paginator = Paginator(events, 12)  # 12 events per page
    page = request.GET.get('page')
    
    try:
        events_page = paginator.page(page)
    except PageNotAnInteger:
        events_page = paginator.page(1)
    except EmptyPage:
        events_page = paginator.page(paginator.num_pages)
    
    # Get all categories for filter
    categories = EventCategory.objects.all()
    
    # Get unique cities
    cities = Event.objects.filter(
        status='published'
    ).values_list('city', flat=True).distinct()
    
    context = {
        'events': events_page,
        'categories': categories,
        'cities': cities,
        'total_count': paginator.count,
        'current_filters': {
            'category': category,
            'city': city,
            'date': date,
            'price_min': price_min,
            'price_max': price_max,
            'is_free': is_free,
            'has_food': has_food,
            'has_drinks': has_drinks,
        }
    }
    
    return render(request, 'events/events_list.html', context)


def event_detail_view(request, id):
    """
    Display detailed information about a single event
    """
    event = get_object_or_404(Event, id=id)
    
    # Increment view count
    Event.objects.filter(pk=event.pk).update(views=F('views') + 1)
    
    # Check if user has favorited (if authenticated)
    is_favorited = False
    user_review = None
    has_tickets = False
    
    if request.user.is_authenticated:
        is_favorited = EventFavorite.objects.filter(
            user=request.user,
            event=event
        ).exists()
        
        # Get user's review if exists
        user_review = EventReview.objects.filter(
            user=request.user,
            event=event
        ).first()
        
        # Check if user has tickets
        has_tickets = Ticket.objects.filter(
            user=request.user,
            event=event
        ).exists()
    
    # Get reviews (exclude user's own review)
    reviews = event.reviews.select_related('user').order_by('-created_at')
    if user_review:
        reviews = reviews.exclude(id=user_review.id)
    
    # Calculate average rating and distribution
    rating_distribution = event.reviews.values('rating').annotate(
        count=Count('rating')
    ).order_by('-rating')
    
    average_rating = event.reviews.aggregate(Avg('rating'))['rating__avg']
    total_reviews = event.reviews.count()
    
    # Get ticket types
    ticket_types = event.ticket_types.filter(is_active=True).order_by('price')
    
    # Calculate distance if user has location
    distance = None
    if request.user.is_authenticated and request.user.latitude and request.user.longitude:
        distance = calculate_distance(
            float(request.user.latitude),
            float(request.user.longitude),
            float(event.latitude),
            float(event.longitude)
        )
        distance = round(distance, 1)
    
    # Get similar events (same category, exclude current)
    similar_events = Event.objects.filter(
        category=event.category,
        status='published',
        start_date__gte=timezone.now().date()
    ).exclude(id=event.id).select_related('category', 'organizer')[:4]
    
    context = {
        'event': event,
        'is_favorited': is_favorited,
        'user_review': user_review,
        'reviews': reviews[:10],  # Show 10 reviews
        'average_rating': average_rating,
        'total_reviews': total_reviews,
        'rating_distribution': rating_distribution,
        'ticket_types': ticket_types,
        'has_tickets': has_tickets,
        'distance': distance,
        'similar_events': similar_events,
    }
    
    return render(request, 'events/event_detail.html', context)


def category_events_view(request, category_name):
    """
    Display events filtered by category
    """
    category = get_object_or_404(EventCategory, name=category_name)
    today = timezone.now().date()
    
    events = Event.objects.filter(
        category=category,
        status='published',
        start_date__gte=today
    ).select_related('organizer').order_by('start_date', 'start_time')
    
    # Annotate with stats
    events = annotate_event_stats(events)
    
    # Pagination
    paginator = Paginator(events, 12)
    page = request.GET.get('page')
    
    try:
        events_page = paginator.page(page)
    except PageNotAnInteger:
        events_page = paginator.page(1)
    except EmptyPage:
        events_page = paginator.page(paginator.num_pages)
    
    context = {
        'category': category,
        'events': events_page,
        'total_count': paginator.count,
    }
    
    return render(request, 'events/category_events.html', context)


def search_events_view(request):
    """
    Search events by query string
    """
    query = request.GET.get('q', '').strip()
    today = timezone.now().date()
    
    if query:
        events = Event.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(venue_name__icontains=query) |
            Q(city__icontains=query) |
            Q(category__name__icontains=query) |
            Q(organizer__organization_name__icontains=query),
            status='published',
            start_date__gte=today
        ).select_related('category', 'organizer').distinct().order_by('start_date')
        
        # Annotate with stats
        events = annotate_event_stats(events)
    else:
        events = Event.objects.none()
    
    # Pagination
    paginator = Paginator(events, 12)
    page = request.GET.get('page')
    
    try:
        events_page = paginator.page(page)
    except PageNotAnInteger:
        events_page = paginator.page(1)
    except EmptyPage:
        events_page = paginator.page(paginator.num_pages)
    
    context = {
        'query': query,
        'events': events_page,
        'total_count': paginator.count,
    }
    
    return render(request, 'events/search_results.html', context)


def nearby_events_view(request):
    """
    Show events near user's location
    """
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login to view nearby events.')
        return redirect('accounts:login')
    
    if not (request.user.latitude and request.user.longitude):
        messages.warning(request, 'Please update your location in profile to view nearby events.')
        return redirect('accounts:profile')
    
    today = timezone.now().date()
    radius = int(request.GET.get('radius', 50))  # Default 50km
    
    # Get all published events
    all_events = Event.objects.filter(
        status='published',
        start_date__gte=today
    ).select_related('category', 'organizer')
    
    # Calculate distances and filter
    nearby_events = []
    for event in all_events:
        distance = calculate_distance(
            float(request.user.latitude),
            float(request.user.longitude),
            float(event.latitude),
            float(event.longitude)
        )
        
        if distance <= radius:
            event.distance = round(distance, 1)
            nearby_events.append(event)
    
    # Sort by distance
    nearby_events.sort(key=lambda x: x.distance)
    
    context = {
        'events': nearby_events,
        'radius': radius,
        'user_location': {
            'lat': float(request.user.latitude),
            'lng': float(request.user.longitude),
        }
    }
    
    return render(request, 'events/nearby_events.html', context)


# ====================================
# FAVORITES
# ====================================

@login_required
@require_POST
def toggle_favorite_view(request, event_id):
    """
    Toggle favorite status for an event
    """
    event = get_object_or_404(Event, id=event_id)
    
    favorite, created = EventFavorite.objects.get_or_create(
        user=request.user,
        event=event
    )
    
    if not created:
        favorite.delete()
        favorited = False
        message = f'Removed {event.title} from favorites.'
    else:
        favorited = True
        message = f'Added {event.title} to favorites.'
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'favorited': favorited,
            'message': message
        })
    
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard:home'))


@login_required
def favorites_list_view(request):
    """
    Display user's favorite events
    """
    today = timezone.now().date()
    
    # Upcoming favorites
    upcoming_favorites = Event.objects.filter(
        favorited_by__user=request.user,
        status='published',
        start_date__gte=today
    ).select_related('category', 'organizer').order_by('start_date')
    
    # Past favorites
    past_favorites = Event.objects.filter(
        favorited_by__user=request.user,
        status='published',
        start_date__lt=today
    ).select_related('category', 'organizer').order_by('-start_date')
    
    context = {
        'upcoming_favorites': upcoming_favorites,
        'past_favorites': past_favorites,
    }
    
    return render(request, 'events/favorites.html', context)


# ====================================
# REVIEWS
# ====================================

@login_required
@require_POST
def add_review_view(request, event_id):
    """
    Add or update review for an event
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user has attended (has tickets for past event)
    has_attended = Ticket.objects.filter(
        user=request.user,
        event=event,
        event__start_date__lt=timezone.now().date()
    ).exists()
    
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')
    
    if not rating:
        messages.error(request, 'Please provide a rating.')
        return redirect('events:detail', slug=event.slug)
    
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        messages.error(request, 'Invalid rating value.')
        return redirect('events:detail', slug=event.slug)
    
    # Create or update review
    review, created = EventReview.objects.update_or_create(
        user=request.user,
        event=event,
        defaults={
            'rating': rating,
            'comment': comment,
            'attended': has_attended
        }
    )
    
    if created:
        messages.success(request, 'Thank you for your review!')
    else:
        messages.success(request, 'Your review has been updated.')
    
    return redirect('events:detail', slug=event.slug)


@login_required
@require_POST
def delete_review_view(request, review_id):
    """
    Delete a review
    """
    review = get_object_or_404(EventReview, id=review_id, user=request.user)
    event_slug = review.event.slug
    review.delete()
    
    messages.success(request, 'Your review has been deleted.')
    return redirect('events:detail', slug=event_slug)


# ====================================
# ORGANIZER VIEWS
# ====================================

@login_required
def create_event_view(request):
    """
    Create a new event (organizers only)
    """
    # Check if user is an organizer
    try:
        organizer = request.user.organizer_profile
    except Organizer.DoesNotExist:
        messages.error(request, 'You need to be an organizer to create events.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = organizer
            event.remaining_capacity = event.total_capacity
            event.save()
            
            messages.success(request, f'Event "{event.title}" created successfully!')
            return redirect('events:detail', slug=event.slug)
    else:
        form = EventForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'events/event_form.html', context)


@login_required
def edit_event_view(request, event_id):
    """
    Edit an existing event (organizers only)
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the organizer of this event
    try:
        if event.organizer != request.user.organizer_profile:
            return HttpResponseForbidden("You don't have permission to edit this event.")
    except Organizer.DoesNotExist:
        return HttpResponseForbidden("You are not an organizer.")
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'Event "{event.title}" updated successfully!')
            return redirect('events:detail', slug=event.slug)
    else:
        form = EventForm(instance=event)
    
    context = {
        'form': form,
        'event': event,
        'action': 'Edit',
    }
    
    return render(request, 'events/event_form.html', context)


@login_required
@require_POST
def delete_event_view(request, event_id):
    """
    Delete an event (organizers only)
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the organizer of this event
    try:
        if event.organizer != request.user.organizer_profile:
            return HttpResponseForbidden("You don't have permission to delete this event.")
    except Organizer.DoesNotExist:
        return HttpResponseForbidden("You are not an organizer.")
    
    # Check if event has any tickets sold
    tickets_sold = event.tickets.count()
    if tickets_sold > 0:
        messages.error(request, 'Cannot delete event with sold tickets. Please cancel it instead.')
        return redirect('events:detail', slug=event.slug)
    
    event_title = event.title
    event.delete()
    
    messages.success(request, f'Event "{event_title}" has been deleted.')
    return redirect('dashboard:home')


@login_required
def my_events_view(request):
    """
    Display events created by the logged-in organizer
    """
    try:
        organizer = request.user.organizer_profile
    except Organizer.DoesNotExist:
        messages.error(request, 'You need to be an organizer to view this page.')
        return redirect('dashboard:home')
    
    events = Event.objects.filter(
        organizer=organizer
    ).annotate(
        tickets_sold_count=Count('tickets'),
        total_revenue=Count('tickets') * F('base_price')
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(events, 10)
    page = request.GET.get('page')
    
    try:
        events_page = paginator.page(page)
    except PageNotAnInteger:
        events_page = paginator.page(1)
    except EmptyPage:
        events_page = paginator.page(paginator.num_pages)
    
    context = {
        'events': events_page,
        'organizer': organizer,
    }
    
    return render(request, 'events/my_events.html', context)


@login_required
def event_analytics_view(request, event_id):
    """
    Display analytics for a specific event (organizers only)
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the organizer
    try:
        if event.organizer != request.user.organizer_profile:
            return HttpResponseForbidden("You don't have permission to view these analytics.")
    except Organizer.DoesNotExist:
        return HttpResponseForbidden("You are not an organizer.")
    
    # Calculate analytics
    total_tickets_sold = event.tickets.count()
    total_revenue = sum(
        order.total_amount for order in event.orders.filter(status='paid')
    )
    platform_commission = sum(
        order.platform_fee for order in event.orders.filter(status='paid')
    )
    net_revenue = total_revenue - platform_commission
    
    favorites_count = event.favorited_by.count()
    reviews_count = event.reviews.count()
    average_rating = event.reviews.aggregate(Avg('rating'))['rating__avg']
    
    # Ticket sales by type
    ticket_sales_by_type = event.ticket_types.annotate(
        sold=Count('tickets')
    ).values('name', 'sold', 'price')
    
    # Recent orders
    recent_orders = event.orders.filter(status='paid').order_by('-created_at')[:10]
    
    context = {
        'event': event,
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': total_revenue,
        'platform_commission': platform_commission,
        'net_revenue': net_revenue,
        'favorites_count': favorites_count,
        'reviews_count': reviews_count,
        'average_rating': average_rating,
        'ticket_sales_by_type': ticket_sales_by_type,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'events/event_analytics.html', context)


# ====================================
# API ENDPOINTS (for AJAX)
# ====================================

@login_required
def check_favorite_status(request, event_id):
    """
    Check if user has favorited an event (AJAX endpoint)
    """
    is_favorited = EventFavorite.objects.filter(
        user=request.user,
        event_id=event_id
    ).exists()
    
    return JsonResponse({'favorited': is_favorited})


def event_calendar_data(request):
    """
    Return events data for calendar view (JSON)
    """
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    events = Event.objects.filter(
        status='published',
        start_date__gte=start_date,
        start_date__lte=end_date
    ).select_related('category')
    
    events_data = []
    for event in events:
        events_data.append({
            'id': str(event.id),
            'title': event.title,
            'start': f"{event.start_date}T{event.start_time}",
            'end': f"{event.end_date}T{event.end_time}",
            'url': f"/events/{event.slug}/",
            'color': '#00F6FF',  # Cyan Glow
            'category': event.category.get_name_display() if event.category else None,
        })
    
    return JsonResponse(events_data, safe=False)