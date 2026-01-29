from unicodedata import category
from django.utils import timezone
from datetime import timedelta, time
from decimal import Decimal
import random

from CheersMe.events.models import Event, EventCategory, Organizer
from CheersMe.tickets.models import TicketType, Ticket, Order, OrderItem
from CheersMe.accounts.models import CustomUser


def run():
    print("🌱 Seeding CheersMe data...")

    # ----------------------------
    # User & Organizer
    # ----------------------------
    user, _ = CustomUser.objects.get_or_create(
        email="organizer@cheersme.com",
        defaults={
            "first_name": "Tendo",
            "last_name": "Organizer",
            "is_active": True,
        }
    )

    organizer, _ = Organizer.objects.get_or_create(
        user=user,
        defaults={
            "organization_name": "Tendo's Bites",
            "phone": "0700000000",
            "email": "tendo@example.com",
            "verified": True,
        }
    )

    # ----------------------------
    # Categories
    # ----------------------------
    category_names = [
        "concert", "party", "business", "wellness",
        "food_offers", "karaoke", "games"
    ]

    categories = []
    for name in category_names:
        cat, _ = EventCategory.objects.get_or_create(name=name)
        categories.append(cat)

    # ----------------------------
    # Events
    # ----------------------------
    venues = [
        ("Kampala Serena Hotel", "Kintu Road", "Kampala"),
        ("Kololo Airstrip", "Kololo", "Kampala"),
        ("Ndere Cultural Centre", "Ntinda", "Kampala"),
    ]

    created_events = []

    for i in range(1, 51):
        venue, address, city = random.choice(venues)
        start_date = timezone.now().date() + timedelta(days=i)

        event, created = Event.objects.get_or_create(
         slug="sample-event-1",
            defaults={

            "organizer": organizer,
            "title": "Sample Event 1",
            "description": "Demo event for CheersMe",
            "category": category,
            "featured_image": "event_images/live_concert.jpg",
            "gallery": [
                "event_images/gallery1.jpg",
                "event_images/gallery2.jpg",
            ],

            "venue_name": venue,
            "address": address,
            "city": city,
            "latitude": Decimal("0.3476"),
            "longitude": Decimal("32.5825"),
            "start_date": start_date,
            "start_time": timezone.now(),
            "end_date": start_date,
            "end_time": timezone.now(),
            "is_free": False,
            "base_price": Decimal("50000"),

            "total_capacity": 200,
            "remaining_capacity": 200,

            "status": "published",
            "is_featured": bool(i % 5 == 0),
            "published_at": timezone.now(),
            }
            
        )
        

        created_events.append(event)

    print(f"✅ {len(created_events)} events created")

    # ----------------------------
    # Ticket Types, Orders & Tickets
    # ----------------------------
    for event in created_events:
        vip = TicketType.objects.create(
            event=event,
            name="VIP",
            price=Decimal("100000"),
            quantity_available=50,
            quantity_sold=0,
            max_per_order=5,
            is_active=True,
        )

        regular = TicketType.objects.create(
            event=event,
            name="Regular",
            price=Decimal("50000"),
            quantity_available=150,
            quantity_sold=0,
            max_per_order=10,
            is_active=True,
        )

        order = Order.objects.create(
            event=event,
            user=user,
            order_number=f"ORD-{event.id.hex[:8]}",
            status="paid",
            subtotal=Decimal("150000"),
            platform_fee=Decimal("5000"),
            total_amount=Decimal("155000"),
            payment_method="mobile_money",
            email=user.email,
            phone="0700000000",
            paid_at=timezone.now(),
        )

        OrderItem.objects.create(
            order=order,
            ticket_type=vip,
            quantity=1,
            price_per_ticket=vip.price,
            subtotal=vip.price,
        )

        Ticket.objects.create(
            event=event,
            order=order,
            user=user,
            ticket_type=vip,
            ticket_number=f"TCK-{random.randint(100000,999999)}",
            attendee_name="Demo Attendee",
            attendee_email=user.email,
            status="valid",
        )

    print("🎟 Tickets & orders created")
    print("🎉 SEEDING COMPLETE")


# IMPORTANT
if __name__ == "__main__":
    run()
