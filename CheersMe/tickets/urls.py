from django.urls import path
from . import views

app_name = 'CheersMe.tickets'

urlpatterns = [
    path('', views.my_tickets_view, name='my_tickets'),
    path('<uuid:ticket_id>/', views.ticket_detail_view, name='detail'),
    path('download/<uuid:ticket_id>/', views.download_ticket_view, name='download'),
]