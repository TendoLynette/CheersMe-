from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('event/<slug:slug>/', views.event_detail_view, name='event_detail'),
    path('category/<str:category_name>/', views.category_events_view, name='category_events'),
    path('search/', views.search_events_view, name='search'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('favorite/toggle/<uuid:event_id>/', views.toggle_favorite_view, name='toggle_favorite'),
    path('my-tickets/', views.my_tickets_view, name='my_tickets'),
    path('ticket/<uuid:ticket_id>/', views.ticket_detail_view, name='ticket_detail'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
]
