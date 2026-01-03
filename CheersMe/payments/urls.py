from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('checkout/<uuid:event_id>/', views.checkout_view, name='checkout'),
    path('payment/', views.payment_view, name='payment'),
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('success/', views.payment_success, name='success'),
    path('webhook/', views.stripe_webhook, name='webhook'),
]
