from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from CheersMe.events.models import Event
from CheersMe.tickets.models import TicketType, Order, OrderItem, Ticket
from CheersMe.notifications.models import Notification
from decimal import Decimal
import stripe
from django.db.models import F
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def checkout_view(request, event_id):
    event = get_object_or_404(Event, id=event_id, status='published')
    ticket_types = TicketType.objects.filter(event=event, is_active=True)

    if request.method == 'POST':
        selected_tickets = []
        total_amount = Decimal('0.00')
        for tt in ticket_types:
            quantity = int(request.POST.get(f'quantity_{tt.id}', 0))
            if quantity > 0:
                if quantity > tt.remaining_tickets:
                    messages.error(request, f'Not enough {tt.name} tickets available.')
                    return redirect('payments:checkout', event_id=event.id)
                selected_tickets.append({'ticket_type': tt, 'quantity': quantity, 'subtotal': tt.price * quantity})
                total_amount += tt.price * quantity

        if not selected_tickets:
            messages.error(request, "Please select at least one ticket.")
            return redirect('payments:checkout', event_id=event.id)

        platform_fee = total_amount * Decimal(str(settings.COMMISSION_RATE))
        final_amount = total_amount + platform_fee

        # Store checkout data in session
        request.session['checkout_data'] = {
            'event_id': str(event.id),
            'tickets': [{'ticket_type_id': t['ticket_type'].id, 'quantity': t['quantity']} for t in selected_tickets],
            'subtotal': str(total_amount),
            'platform_fee': str(platform_fee),
            'total': str(final_amount)
        }

        return redirect('payments:payment')

    return render(request, 'payments/checkout.html', {
        'event': event,
        'ticket_types': ticket_types,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    })


@login_required
def payment_view(request):
    checkout_data = request.session.get('checkout_data')
    if not checkout_data:
        messages.error(request, 'No checkout data found.')
        return redirect('dashboard:home')

    event = get_object_or_404(Event, id=checkout_data['event_id'])
    return render(request, 'payments/payment.html', {
        'event': event,
        'checkout_data': checkout_data,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    })


@login_required
def create_payment_intent(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    checkout_data = request.session.get('checkout_data')
    if not checkout_data:
        return JsonResponse({'error': 'No checkout data found'}, status=400)

    try:
        # Stripe expects amount in cents (or lowest currency unit)
        amount = int(Decimal(checkout_data['total']))
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='ugx',  # Ugandan Shillings
            metadata={
                'user_id': request.user.id,
                'event_id': checkout_data['event_id'],
            }
        )
        return JsonResponse({'clientSecret': intent.client_secret})

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

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if intent.status == 'succeeded':
            with transaction.atomic():
                event = get_object_or_404(Event, id=checkout_data['event_id'])

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
                    phone='',
                    paid_at=timezone.now()
                )

                for t in checkout_data['tickets']:
                    ticket_type = TicketType.objects.get(id=t['ticket_type_id'])
                    OrderItem.objects.create(
                        order=order,
                        ticket_type=ticket_type,
                        quantity=t['quantity'],
                        price_per_ticket=ticket_type.price
                    )

                    for _ in range(t['quantity']):
                        Ticket.objects.create(
                            order=order,
                            ticket_type=ticket_type,
                            user=request.user,
                            event=event,
                            attendee_name=request.user.get_full_name(),
                            attendee_email=request.user.email
                        )

                    ticket_type.quantity_sold = F('quantity_sold') + t['quantity']
                    ticket_type.save(update_fields=['quantity_sold'])

                # Update event capacity
                event.remaining_capacity -= sum(t['quantity'] for t in checkout_data['tickets'])
                event.save()

                # Create notification
                Notification.objects.create(
                    user=request.user,
                    notification_type='ticket_purchased',
                    title='Tickets Purchased Successfully',
                    message=f'You have successfully purchased tickets for {event.title}',
                    event=event,
                    link='/dashboard/my-tickets/'
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
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'payment_intent.succeeded':
        handle_successful_payment(event['data']['object'])
    elif event['type'] == 'payment_intent.payment_failed':
        handle_failed_payment(event['data']['object'])

    return HttpResponse(status=200)


def handle_successful_payment(payment_intent):
    print(f"Payment succeeded: {payment_intent['id']}")


def handle_failed_payment(payment_intent):
    print(f"Payment failed: {payment_intent['id']}")


def send_ticket_confirmation_email(user, order):
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
