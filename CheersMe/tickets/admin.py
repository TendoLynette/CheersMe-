from django.contrib import admin
from .models import TicketType, Order, Ticket, OrderItem

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ['event', 'name', 'price', 'quantity_available', 'quantity_sold', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['event__title', 'name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'event', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'user__email', 'event__title']
    readonly_fields = ['id', 'order_number', 'created_at', 'updated_at', 'paid_at']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'user', 'event', 'status', 'checked_in', 'created_at']
    list_filter = ['status', 'checked_in', 'created_at']
    search_fields = ['ticket_number', 'user__email', 'event__title', 'attendee_name']
    readonly_fields = ['id', 'ticket_number', 'qr_code', 'created_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'ticket_type', 'quantity', 'price_per_ticket', 'subtotal']
    search_fields = ['order__order_number']