from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Public event views
    path('', views.events_list_view, name='list'),
    path('search/', views.search_events_view, name='search'),
    path('nearby/', views.nearby_events_view, name='nearby'),
    path('category/<str:category_name>/', views.category_events_view, name='category'),
    path('<slug:slug>/', views.event_detail_view, name='detail'),
    
    # Favorites
    path('favorite/toggle/<uuid:event_id>/', views.toggle_favorite_view, name='toggle_favorite'),
    path('favorites/', views.favorites_list_view, name='favorites'),
    path('favorite/check/<uuid:event_id>/', views.check_favorite_status, name='check_favorite'),
    
    # Reviews
    path('<uuid:event_id>/review/add/', views.add_review_view, name='add_review'),
    path('review/<int:review_id>/delete/', views.delete_review_view, name='delete_review'),
    
    # Organizer views
    path('create/', views.create_event_view, name='create'),
    path('<uuid:event_id>/edit/', views.edit_event_view, name='edit'),
    path('<uuid:event_id>/delete/', views.delete_event_view, name='delete'),
    path('my-events/', views.my_events_view, name='my_events'),
    path('<uuid:event_id>/analytics/', views.event_analytics_view, name='analytics'),
    
    # API endpoints
    path('api/calendar/', views.event_calendar_data, name='calendar_data'),
]