from django.db import models
from CheersMe.accounts.models import CustomUser
from CheersMe.events.models import Event
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

class TicketType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    name = models.CharField(max_length=100)  # e.g., "VIP", "General Admission", "Early Bird"
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)
    
    # Restrictions
    max_per_order = models.PositiveIntegerField(default=10)
    sale_start_date = models.DateTimeField(null=True, blank=True)
    sale_end_date = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.event.title} - {self.name}"
    
    @property
    def is_available(self):
        return self.is_active and self.quantity_sold < self.quantity_available
    
    @property
    def remaining_tickets(self):
        return self.quantity_available - self.quantity_sold
    
    class Meta:
        ordering = ['price']

class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='orders')
    
    # Order details
    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)  # 2% commission
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment
    payment_method = models.CharField(max_length=50, blank=True)
    payment_intent_id = models.CharField(max_length=200, blank=True)  # Stripe payment intent
    
    # Contact information
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    def generate_order_number(self):
        return f"CM{self.created_at.strftime('%Y%m%d')}{str(self.id)[:8].upper()}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            super().save(*args, **kwargs)
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']

class Ticket(models.Model):
    TICKET_STATUS = [
        ('valid', 'Valid'),
        ('used', 'Used'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tickets')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    
    # Ticket details
    ticket_number = models.CharField(max_length=50, unique=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    status = models.CharField(max_length=20, choices=TICKET_STATUS, default='valid')
    
    # Attendee information
    attendee_name = models.CharField(max_length=200)
    attendee_email = models.EmailField()
    
    # Usage tracking
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"CHEERSME-{self.ticket_number}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        file_name = f'qr_{self.ticket_number}.png'
        self.qr_code.save(file_name, File(buffer), save=False)
        buffer.close()
    
    def generate_ticket_number(self):
        return f"TKT{self.created_at.strftime('%Y%m%d')}{str(self.id)[:8].upper()}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            super().save(*args, **kwargs)
            self.ticket_number = self.generate_ticket_number()
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Ticket {self.ticket_number}"
    
    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_per_ticket = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}x {self.ticket_type.name}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price_per_ticket
        super().save(*args, **kwargs)