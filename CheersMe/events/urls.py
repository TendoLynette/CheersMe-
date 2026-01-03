from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.events_list_view, name='list'),
    path('<slug:slug>/', views.event_detail_view, name='detail'),
    path('category/<str:category>/', views.category_events_view, name='category'),
]