from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # User Ticket Views
    path('my-tickets/', views.my_tickets_view, name='my_tickets'),
    path('ticket/<uuid:ticket_id>/', views.ticket_detail_view, name='detail'),
    path('ticket/<uuid:ticket_id>/download/', views.download_ticket_pdf, name='download_pdf'),
    path('ticket/<uuid:ticket_id>/email/', views.email_ticket_view, name='email_ticket'),
    
    # Order Views
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('order/<uuid:order_id>/', views.order_detail_view, name='order_detail'),
    path('order/<uuid:order_id>/receipt/', views.download_order_receipt, name='download_receipt'),
    path('order/<uuid:order_id>/cancel/', views.cancel_order_view, name='cancel_order'),
    
    # Organizer Views (Ticket Validation)
    path('validate/', views.validate_ticket_view, name='validate'),
    path('check-in/<str:ticket_number>/', views.check_in_ticket, name='check_in'),
    path('event/<uuid:event_id>/tickets/', views.event_tickets_list, name='event_tickets'),
    path('event/<uuid:event_id>/export/', views.export_tickets_csv, name='export_csv'),
    
    # API Endpoints
    path('api/ticket/<uuid:ticket_id>/status/', views.ticket_status_api, name='ticket_status_api'),
    path('api/order/<uuid:order_id>/status/', views.order_status_api, name='order_status_api'),
]