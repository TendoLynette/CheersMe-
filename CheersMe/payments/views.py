from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from events.models import Event
from tickets.models import TicketType, Order, OrderItem, Ticket
from notifications.models import Notification
from decimal import Decimal
import stripe
import json

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def checkout_view(request, event_id):
    event = get_object_or_404(Event, id=event_id, status='published')
    ticket_types = event.ticket_types.filter(is_active=True)
    
    if request.method == 'POST':
        # Get selected tickets from form
        selected_tickets = []
        total_amount = Decimal('0.00')
        
        for ticket_type in ticket_types:
            quantity = int(request.POST.get(f'quantity_{ticket_type.id}', 0))
            if quantity > 0:
                if quantity > ticket_type.remaining_tickets:
                    messages.error(request, f'Not enough {ticket_type.name} tickets available.')
                    return redirect('payments:checkout', event_id=event.id)
                
                selected_tickets.append({
                    'ticket_type': ticket_type,
                    'quantity': quantity,
                    'subtotal': ticket_type.price * quantity
                })
                total_amount += ticket_type.price * quantity
        
        if not selected_tickets:
            messages.error(request, 'Please select at least one ticket.')
            return redirect('payments:checkout', event_id=event.id)
        
        # Calculate platform fee (2% commission)
        platform_fee = total_amount * Decimal(str(settings.COMMISSION_RATE))
        final_amount = total_amount + platform_fee
        
        # Store in session
        request.session['checkout_data'] = {
            'event_id': str(event.id),
            'tickets': [
                {
                    'ticket_type_id': item['ticket_type'].id,
                    'quantity': item['quantity']
                } for item in selected_tickets
            ],
            'subtotal': str(total_amount),
            'platform_fee': str(platform_fee),
            'total': str(final_amount)
        }
        
        return redirect('payments:payment')
    
    context = {
        'event': event,
        'ticket_types': ticket_types,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, 'payments/checkout.html', context)

@login_required
def payment_view(request):
    checkout_data = request.session.get('checkout_data')
    
    if not checkout_data:
        messages.error(request, 'No checkout data found.')
        return redirect('dashboard:home')
    
    event = get_object_or_404(Event, id=checkout_data['event_id'])
    
    context = {
        'event': event,
        'checkout_data': checkout_data,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, 'payments/payment.html', context)

@login_required
def create_payment_intent(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    checkout_data = request.session.get('checkout_data')
    if not checkout_data:
        return JsonResponse({'error': 'No checkout data'}, status=400)
    
    try:
        # Create Stripe payment intent
        amount_cents = int(Decimal(checkout_data['total']) * 100)  # Convert to cents
        
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='ugx',  # Ugandan Shillings
            metadata={
                'user_id': request.user.id,
                'event_id': checkout_data['event_id'],
            }
        )
        
        return JsonResponse({
            'clientSecret': intent.client_secret
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def payment_success(request):
    checkout_data = request.session.get('checkout_data')
    
    if not checkout_data:
        messages.error(request, 'No checkout data found.')
        return redirect('dashboard:home')
    
    payment_intent_id = request.GET.get('payment_intent')
    
    if not payment_intent_id:
        messages.error(request, 'Invalid payment.')
        return redirect('dashboard:home')
    
    # Verify payment with Stripe
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == 'succeeded':
            # Create order
            event = Event.objects.get(id=checkout_data['event_id'])
            
            order = Order.objects.create(
                user=request.user,
                event=event,
                status='paid',
                subtotal=Decimal(checkout_data['subtotal']),
                platform_fee=Decimal(checkout_data['platform_fee']),
                total_amount=Decimal(checkout_data['total']),
                payment_method='stripe',
                payment_intent_id=payment_intent_id,
                email=request.user.email,
                phone=request.user.phone_number or '',
                paid_at=timezone.now()
            )
            
            # Create order items and tickets
            for ticket_data in checkout_data['tickets']:
                ticket_type = TicketType.objects.get(id=ticket_data['ticket_type_id'])
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    ticket_type=ticket_type,
                    quantity=ticket_data['quantity'],
                    price_per_ticket=ticket_type.price
                )
                
                # Create tickets
                for _ in range(ticket_data['quantity']):
                    Ticket.objects.create(
                        order=order,
                        ticket_type=ticket_type,
                        user=request.user,
                        event=event,
                        attendee_name=request.user.get_full_name(),
                        attendee_email=request.user.email
                    )
                
                # Update ticket type sold count
                ticket_type.quantity_sold += ticket_data['quantity']
                ticket_type.save()
            
            # Update event capacity
            total_tickets = sum(item['quantity'] for item in checkout_data['tickets'])
            event.remaining_capacity -= total_tickets
            event.save()
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                notification_type='ticket_purchased',
                title='Tickets Purchased Successfully',
                message=f'You have successfully purchased tickets for {event.title}',
                event=event,
                link=f'/dashboard/my-tickets/'
            )
            
            # Send confirmation email
            send_ticket_confirmation_email(request.user, order)
            
            # Clear session
            del request.session['checkout_data']
            
            messages.success(request, 'Payment successful! Your tickets have been sent to your email.')
            return render(request, 'payments/success.html', {'order': order})
    
    except Exception as e:
        messages.error(request, f'Payment verification failed: {str(e)}')
        return redirect('dashboard:home')
    
    messages.error(request, 'Payment not completed.')
    return redirect('dashboard:home')

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Handle successful payment
        handle_successful_payment(payment_intent)
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        # Handle failed payment
        handle_failed_payment(payment_intent)
    
    return HttpResponse(status=200)

def handle_successful_payment(payment_intent):
    # Additional processing for successful payments
    pass

def handle_failed_payment(payment_intent):
    # Handle failed payments
    pass

def send_ticket_confirmation_email(user, order):
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    subject = f'Your Tickets for {order.event.title}'
    html_message = render_to_string('emails/ticket_confirmation.html', {
        'user': user,
        'order': order,
        'tickets': order.tickets.all()
    })
    
    try:
        send_mail(
            subject,
            'Your ticket details',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending ticket confirmation: {e}")