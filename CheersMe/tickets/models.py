from django.db import models
from CheersMe.accounts.models import CustomUser
from CheersMe.events.models import Event
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
from django.utils import timezone
from django.db import transaction



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
    
    
    
    def mark_as_paid(self, payment_method="mock"):
       if self.status == "paid":
          return  # Prevent double processing

       with transaction.atomic():
        self.status = "paid"
        self.payment_method = payment_method
        self.paid_at = timezone.now()
        self.save()

        # Create tickets
        for item in self.items.all():
            for _ in range(item.quantity):
                Ticket.objects.create(
                    order=self,
                    ticket_type=item.ticket_type,
                    user=self.user,
                    event=self.event,
                    attendee_name=self.user.get_full_name() or self.user.username,
                    attendee_email=self.email,
                )

            # Update ticket type counts
            item.ticket_type.quantity_sold += item.quantity
            item.ticket_type.save()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    # Order identity
    order_number = models.CharField(max_length=50, unique=True, editable=False)

    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS,
        default='pending'
    )

    # Pricing (calculated server-side)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment (future-proof)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_intent_id = models.CharField(max_length=200, blank=True)

    # Contact info at time of purchase
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order {self.order_number}"

    def generate_order_number(self):
        return f"CM-{uuid.uuid4().hex[:10].upper()}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            for _ in range(5):  # retry safety
                candidate = self.generate_order_number()
                if not Order.objects.filter(order_number=candidate).exists():
                    self.order_number = candidate
                    break
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
        return f"TKT{uuid.uuid4().hex[:12].upper()}"

    
    def save(self, *args, **kwargs):
     if not self.ticket_number:
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