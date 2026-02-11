from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime, timedelta
from io import BytesIO
import json

from django.db import transaction
from decimal import Decimal
from .models import Ticket, Order, OrderItem, TicketType
from CheersMe.events.models import Event
from CheersMe.notifications.models import Notification

# PDF Generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ====================================
# USER TICKET VIEWS
# ====================================

@login_required
def my_tickets_view(request):
    """
    Display all tickets for the logged-in user
    """
    # Get filter parameters
    status = request.GET.get('status', 'all')
    time_filter = request.GET.get('time', 'all')
    
    # Base queryset
    tickets = Ticket.objects.filter(
        user=request.user
    ).select_related(
        'event', 'ticket_type', 'order'
    ).order_by('-created_at')
    
    # Apply status filter
    if status != 'all':
        tickets = tickets.filter(status=status)
    
    # Apply time filter
    today = timezone.now().date()
    if time_filter == 'upcoming':
        tickets = tickets.filter(event__start_date__gte=today)
    elif time_filter == 'past':
        tickets = tickets.filter(event__start_date__lt=today)
    elif time_filter == 'today':
        tickets = tickets.filter(event__start_date=today)
    
    # Group tickets by event
    events_with_tickets = {}
    for ticket in tickets:
        event_id = ticket.event.id
        if event_id not in events_with_tickets:
            events_with_tickets[event_id] = {
                'event': ticket.event,
                'tickets': [],
                'order': ticket.order
            }
        events_with_tickets[event_id]['tickets'].append(ticket)
    
    # Statistics
    total_tickets = tickets.count()
    upcoming_tickets = tickets.filter(event__start_date__gte=today).count()
    used_tickets = tickets.filter(checked_in=True).count()
    
    context = {
        'events_with_tickets': events_with_tickets.values(),
        'total_tickets': total_tickets,
        'upcoming_tickets': upcoming_tickets,
        'used_tickets': used_tickets,
        'current_filter': {
            'status': status,
            'time': time_filter
        }
    }
    
    return render(request, 'tickets/my_tickets.html', context)


@login_required
def ticket_detail_view(request, ticket_id):
    """
    Display detailed information about a single ticket with QR code
    """
    ticket = get_object_or_404(
        Ticket.objects.select_related('event', 'ticket_type', 'order'),
        id=ticket_id,
        user=request.user
    )
    
    # Check if event has started
    event_started = ticket.event.start_date < timezone.now().date()
    
    # Check if ticket is still valid
    is_valid = (
        ticket.status == 'valid' and 
        not ticket.checked_in and
        ticket.event.start_date >= timezone.now().date()
    )
    
    context = {
        'ticket': ticket,
        'event_started': event_started,
        'is_valid': is_valid,
    }
    
    return render(request, 'tickets/ticket_detail.html', context)


@login_required
def download_ticket_pdf(request, ticket_id):
    """
    Generate and download ticket as PDF
    """
    if not REPORTLAB_AVAILABLE:
        messages.error(request, 'PDF generation is not available.')
        return redirect('tickets:detail', ticket_id=ticket_id)
    
    ticket = get_object_or_404(
        Ticket.objects.select_related('event', 'ticket_type', 'order'),
        id=ticket_id,
        user=request.user
    )
    
    # Create PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Colors
    cyan = (0, 246/255, 255/255)
    purple = (176/255, 55/255, 148/255)
    
    # Header with gradient effect (simplified)
    p.setFillColorRGB(*cyan)
    p.rect(0, height-120, width, 120, fill=True, stroke=False)
    
    # Logo/Title
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 36)
    p.drawString(50, height-70, "CheersMe")
    
    p.setFont("Helvetica", 16)
    p.drawString(50, height-95, "Your Event Ticket")
    
    # Ticket Information
    y = height - 160
    p.setFillColorRGB(0, 0, 0)
    
    # Event Title
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, y, ticket.event.title)
    y -= 40
    
    # Event Details
    p.setFont("Helvetica", 12)
    details = [
        f"Ticket Number: {ticket.ticket_number}",
        f"Ticket Type: {ticket.ticket_type.name}",
        f"Attendee: {ticket.attendee_name}",
        f"Date: {ticket.event.start_date.strftime('%B %d, %Y')}",
        f"Time: {ticket.event.start_time.strftime('%I:%M %p')}",
        f"Venue: {ticket.event.venue_name}",
        f"Location: {ticket.event.address}, {ticket.event.city}",
    ]
    
    for detail in details:
        p.drawString(50, y, detail)
        y -= 25
    
    # QR Code
    if ticket.qr_code:
        try:
            qr_path = ticket.qr_code.path
            img = ImageReader(qr_path)
            p.drawImage(img, width-250, y-150, width=200, height=200, preserveAspectRatio=True)
        except:
            pass
    
    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 50, "Scan QR code at the venue entrance")
    p.drawString(50, 35, f"Order #{ticket.order.order_number}")
    
    # Watermark if used
    if ticket.checked_in:
        p.setFillColorRGB(0.9, 0.9, 0.9)
        p.setFont("Helvetica-Bold", 60)
        p.saveState()
        p.translate(width/2, height/2)
        p.rotate(45)
        p.drawCentredString(0, 0, "USED")
        p.restoreState()
    
    p.showPage()
    p.save()
    
    # Get PDF from buffer
    buffer.seek(0)
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'
    response.write(pdf)
    
    return response


@login_required
def email_ticket_view(request, ticket_id):
    """
    Email ticket to user
    """
    ticket = get_object_or_404(
        Ticket.objects.select_related('event', 'ticket_type', 'order'),
        id=ticket_id,
        user=request.user
    )
    
    # Prepare email
    subject = f'Your Ticket for {ticket.event.title}'
    html_message = render_to_string('emails/ticket_email.html', {
        'ticket': ticket,
        'user': request.user,
    })
    
    email = EmailMessage(
        subject,
        html_message,
        settings.DEFAULT_FROM_EMAIL,
        [request.user.email]
    )
    email.content_subtype = 'html'
    
    # Attach QR code if available
    if ticket.qr_code:
        try:
            email.attach_file(ticket.qr_code.path)
        except:
            pass
    
    try:
        email.send()
        messages.success(request, f'Ticket emailed to {request.user.email}')
    except Exception as e:
        messages.error(request, f'Failed to send email: {str(e)}')
    
    return redirect('tickets:detail', ticket_id=ticket.id)


@login_required
def buy_ticket(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    order = Order.objects.create(
        user=request.user,
        event=event,
        quantity=1,
        total_price=event.ticket_price
    )

    return redirect('order_detail', order.id)




# ====================================
# ORDER VIEWS
# ====================================

@login_required
def my_orders_view(request):
    """
    Display all orders for the logged-in user
    """
    orders = Order.objects.filter(
        user=request.user
    ).select_related('event').prefetch_related(
        'items__ticket_type', 'tickets'
    ).order_by('-created_at')
    
    # Apply status filter
    status = request.GET.get('status', 'all')
    if status != 'all':
        orders = orders.filter(status=status)
    
    # Pagination
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)
    
    # Statistics
    total_spent = Order.objects.filter(
        user=request.user,
        status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    total_orders = Order.objects.filter(user=request.user).count()
    paid_orders = Order.objects.filter(user=request.user, status='paid').count()
    
    context = {
        'orders': orders_page,
        'total_spent': total_spent,
        'total_orders': total_orders,
        'paid_orders': paid_orders,
        'current_status': status,
    }
    
    return render(request, 'tickets/my_orders.html', context)


@login_required
def order_detail_view(request, order_id):
    """
    Display detailed information about a specific order
    """
    order = get_object_or_404(
        Order.objects.select_related('event', 'user').prefetch_related(
            'items__ticket_type', 'tickets__ticket_type'
        ),
        id=order_id,
        user=request.user
    )
    
    # Group tickets by type
    tickets_by_type = {}
    for ticket in order.tickets.all():
        ticket_type_name = ticket.ticket_type.name
        if ticket_type_name not in tickets_by_type:
            tickets_by_type[ticket_type_name] = []
        tickets_by_type[ticket_type_name].append(ticket)
    
    context = {
        'order': order,
        'tickets_by_type': tickets_by_type,
    }
    
    return render(request, 'tickets/order_detail.html', context)


@login_required
def download_order_receipt(request, order_id):
    """
    Generate and download order receipt as PDF
    """
    if not REPORTLAB_AVAILABLE:
        messages.error(request, 'PDF generation is not available.')
        return redirect('tickets:order_detail', order_id=order_id)
    
    order = get_object_or_404(
        Order.objects.select_related('event').prefetch_related('items__ticket_type'),
        id=order_id,
        user=request.user
    )
    
    # Create PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    p.setFillColorRGB(0, 246/255, 255/255)
    p.rect(0, height-100, width, 100, fill=True, stroke=False)
    
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 28)
    p.drawString(50, height-60, "Order Receipt")
    
    # Order Information
    y = height - 130
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, f"Order Number: {order.order_number}")
    y -= 25
    
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}")
    y -= 20
    p.drawString(50, y, f"Status: {order.get_status_display()}")
    y -= 40
    
    # Customer Information
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Customer Information")
    y -= 25
    
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Name: {order.user.get_full_name()}")
    y -= 20
    p.drawString(50, y, f"Email: {order.email}")
    y -= 20
    p.drawString(50, y, f"Phone: {order.phone}")
    y -= 40
    
    # Event Information
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Event Information")
    y -= 25
    
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Event: {order.event.title}")
    y -= 20
    p.drawString(50, y, f"Date: {order.event.start_date.strftime('%B %d, %Y')}")
    y -= 20
    p.drawString(50, y, f"Venue: {order.event.venue_name}")
    y -= 40
    
    # Order Items
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Order Items")
    y -= 25
    
    # Table header
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Item")
    p.drawString(300, y, "Quantity")
    p.drawString(400, y, "Price")
    p.drawString(500, y, "Subtotal")
    y -= 20
    
    # Line
    p.line(50, y, width-50, y)
    y -= 15
    
    # Items
    p.setFont("Helvetica", 11)
    for item in order.items.all():
        p.drawString(50, y, item.ticket_type.name)
        p.drawString(300, y, str(item.quantity))
        p.drawString(400, y, f"UGX {item.price_per_ticket:,.2f}")
        p.drawString(500, y, f"UGX {item.subtotal:,.2f}")
        y -= 20
    
    y -= 10
    p.line(50, y, width-50, y)
    y -= 25
    
    # Totals
    p.setFont("Helvetica-Bold", 12)
    p.drawString(400, y, "Subtotal:")
    p.drawString(500, y, f"UGX {order.subtotal:,.2f}")
    y -= 20
    
    p.drawString(400, y, "Platform Fee (2%):")
    p.drawString(500, y, f"UGX {order.platform_fee:,.2f}")
    y -= 20
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(400, y, "Total:")
    p.drawString(500, y, f"UGX {order.total_amount:,.2f}")
    
    # Footer
    y = 80
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, y, "Thank you for your purchase!")
    y -= 15
    p.drawString(50, y, "CheersMe - Discover Amazing Events")
    
    if order.status == 'paid':
        y -= 15
        p.drawString(50, y, f"Payment Method: {order.payment_method}")
        y -= 15
        p.drawString(50, y, f"Transaction ID: {order.payment_intent_id}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{order.order_number}.pdf"'
    response.write(pdf)
    
    return response

@login_required
@transaction.atomic
def create_order(request, event_slug):
    if request.method != "POST":
        return redirect("events:detail", slug=event_slug)

    event = get_object_or_404(Event, slug=event_slug)

    ticket_type_id = request.POST.get("ticket_type")
    quantity = int(request.POST.get("quantity", 1))

    ticket_type = get_object_or_404(
        TicketType,
        id=ticket_type_id,
        event=event,
        is_active=True
    )

    # ✅ Validations
    if quantity < 1:
        return redirect("events:detail", slug=event_slug)

    if quantity > ticket_type.remaining_tickets:
        return redirect("events:detail", slug=event_slug)

    if quantity > ticket_type.max_per_order:
        return redirect("events:detail", slug=event_slug)

    # 💰 Calculations (SERVER SIDE)
    subtotal = ticket_type.price * quantity
    platform_fee = subtotal * Decimal("0.02")  # 2%
    total = subtotal + platform_fee

    # 🧾 Create Order
    order = Order.objects.create(
        user=request.user,
        event=event,
        status="PENDING",
        subtotal=subtotal,
        platform_fee=platform_fee,
        total_amount=total,
        email=request.user.email,
        phone=getattr(request.user, "phone", "")
    )

    # 📦 Create Order Item
    OrderItem.objects.create(
        order=order,
        ticket_type=ticket_type,
        quantity=quantity,
        price_per_ticket=ticket_type.price
    )

    return redirect("tickets:order_detail", order_id=order.id)
    






@login_required
@require_POST
def cancel_order_view(request, order_id):
    """
    Cancel an order (only if not paid and within cancellation period)
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order can be cancelled
    if order.status == 'paid':
        messages.error(request, 'Cannot cancel a paid order. Please contact support for refunds.')
        return redirect('tickets:order_detail', order_id=order.id)
    
    if order.status == 'cancelled':
        messages.warning(request, 'This order is already cancelled.')
        return redirect('tickets:order_detail', order_id=order.id)
    
    # Cancel the order
    order.status = 'cancelled'
    order.save()
    
    # Cancel all tickets
    order.tickets.update(status='cancelled')
    
    # Restore event capacity
    total_tickets = order.tickets.count()
    Event.objects.filter(id=order.event.id).update(
        remaining_capacity=F('remaining_capacity') + total_tickets
    )
    
    # Restore ticket type quantities
    for item in order.items.all():
        TicketType.objects.filter(id=item.ticket_type.id).update(
            quantity_sold=F('quantity_sold') - item.quantity
        )
    
    messages.success(request, 'Order cancelled successfully.')
    return redirect('tickets:my_orders')


# ====================================
# ORGANIZER VIEWS (Ticket Validation)
# ====================================

@login_required
def validate_ticket_view(request):
    """
    View for organizers to validate/check-in tickets
    """
    # Check if user is an organizer
    try:
        organizer = request.user.organizer_profile
    except:
        messages.error(request, 'You must be an organizer to access this page.')
        return redirect('dashboard:home')
    
    # Get organizer's events
    events = Event.objects.filter(organizer=organizer).order_by('-start_date')
    
    context = {
        'events': events,
    }
    
    return render(request, 'tickets/validate_ticket.html', context)


@login_required
@require_POST
def check_in_ticket(request, ticket_number):
    """
    Check in a ticket by ticket number or QR code (AJAX endpoint)
    """
    # Verify organizer
    try:
        organizer = request.user.organizer_profile
    except:
        return JsonResponse({
            'success': False,
            'message': 'You must be an organizer to check in tickets.'
        }, status=403)
    
    # Find ticket
    try:
        ticket = Ticket.objects.select_related('event', 'user', 'ticket_type').get(
            ticket_number=ticket_number
        )
    except Ticket.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Ticket not found.'
        })
    
    # Verify organizer owns this event
    if ticket.event.organizer != organizer:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to check in this ticket.'
        }, status=403)
    
    # Check ticket status
    if ticket.status != 'valid':
        return JsonResponse({
            'success': False,
            'message': f'Ticket is {ticket.status}. Cannot check in.'
        })
    
    if ticket.checked_in:
        return JsonResponse({
            'success': False,
            'message': f'Ticket already checked in at {ticket.checked_in_at.strftime("%I:%M %p on %B %d, %Y")}.',
            'ticket_info': {
                'ticket_number': ticket.ticket_number,
                'attendee': ticket.attendee_name,
                'ticket_type': ticket.ticket_type.name,
                'checked_in': True,
                'checked_in_at': ticket.checked_in_at.isoformat()
            }
        })
    
    # Check in the ticket
    ticket.checked_in = True
    ticket.checked_in_at = timezone.now()
    ticket.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Ticket checked in successfully!',
        'ticket_info': {
            'ticket_number': ticket.ticket_number,
            'attendee': ticket.attendee_name,
            'attendee_email': ticket.attendee_email,
            'ticket_type': ticket.ticket_type.name,
            'event': ticket.event.title,
            'checked_in': True,
            'checked_in_at': ticket.checked_in_at.isoformat()
        }
    })


@login_required
def event_tickets_list(request, event_id):
    """
    List all tickets for a specific event (organizers only)
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Verify organizer
    try:
        organizer = request.user.organizer_profile
        if event.organizer != organizer:
            return HttpResponseForbidden("You don't have permission to view these tickets.")
    except:
        return HttpResponseForbidden("You must be an organizer.")
    
    # Get tickets with filters
    status = request.GET.get('status', 'all')
    checked_in = request.GET.get('checked_in', 'all')
    
    tickets = Ticket.objects.filter(
        event=event
    ).select_related('user', 'ticket_type', 'order').order_by('-created_at')
    
    if status != 'all':
        tickets = tickets.filter(status=status)
    
    if checked_in == 'yes':
        tickets = tickets.filter(checked_in=True)
    elif checked_in == 'no':
        tickets = tickets.filter(checked_in=False)
    
    # Statistics
    total_tickets = Ticket.objects.filter(event=event).count()
    checked_in_count = Ticket.objects.filter(event=event, checked_in=True).count()
    valid_tickets = Ticket.objects.filter(event=event, status='valid').count()
    
    # Tickets by type
    tickets_by_type = Ticket.objects.filter(event=event).values(
        'ticket_type__name'
    ).annotate(
        count=Count('id'),
        checked_in_count=Count('id', filter=Q(checked_in=True))
    )
    
    # Pagination
    paginator = Paginator(tickets, 50)
    page = request.GET.get('page')
    
    try:
        tickets_page = paginator.page(page)
    except PageNotAnInteger:
        tickets_page = paginator.page(1)
    except EmptyPage:
        tickets_page = paginator.page(paginator.num_pages)
    
    context = {
        'event': event,
        'tickets': tickets_page,
        'total_tickets': total_tickets,
        'checked_in_count': checked_in_count,
        'valid_tickets': valid_tickets,
        'tickets_by_type': tickets_by_type,
        'current_filters': {
            'status': status,
            'checked_in': checked_in
        }
    }
    
    return render(request, 'tickets/event_tickets_list.html', context)


@login_required
def export_tickets_csv(request, event_id):
    """
    Export event tickets as CSV (organizers only)
    """
    import csv
    
    event = get_object_or_404(Event, id=event_id)
    
    # Verify organizer
    try:
        organizer = request.user.organizer_profile
        if event.organizer != organizer:
            return HttpResponseForbidden("You don't have permission to export these tickets.")
    except:
        return HttpResponseForbidden("You must be an organizer.")
    
    # Create CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tickets_{event.slug}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Ticket Number', 'Attendee Name', 'Attendee Email', 
        'Ticket Type', 'Order Number', 'Status', 
        'Checked In', 'Checked In At', 'Purchase Date'
    ])
    
    tickets = Ticket.objects.filter(event=event).select_related(
        'ticket_type', 'order'
    ).order_by('-created_at')
    
    for ticket in tickets:
        writer.writerow([
            ticket.ticket_number,
            ticket.attendee_name,
            ticket.attendee_email,
            ticket.ticket_type.name,
            ticket.order.order_number,
            ticket.status,
            'Yes' if ticket.checked_in else 'No',
            ticket.checked_in_at.strftime('%Y-%m-%d %I:%M %p') if ticket.checked_in_at else '',
            ticket.created_at.strftime('%Y-%m-%d %I:%M %p')
        ])
    
    return response


# ====================================
# API ENDPOINTS
# ====================================

@login_required
def ticket_status_api(request, ticket_id):
    """
    Get ticket status (AJAX endpoint)
    """
    try:
        ticket = Ticket.objects.select_related('event').get(
            id=ticket_id,
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'ticket': {
                'id': str(ticket.id),
                'ticket_number': ticket.ticket_number,
                'status': ticket.status,
                'checked_in': ticket.checked_in,
                'event_title': ticket.event.title,
                'event_date': ticket.event.start_date.isoformat(),
            }
        })
    except Ticket.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Ticket not found'
        }, status=404)


@login_required
def order_status_api(request, order_id):
    """
    Get order status (AJAX endpoint)
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'order': {
                'id': str(order.id),
                'order_number': order.order_number,
                'status': order.status,
                'total_amount': float(order.total_amount),
                'tickets_count': order.tickets.count(),
            }
        })
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Order not found'
        }, status=404)
        
        
