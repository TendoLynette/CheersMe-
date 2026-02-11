import random
import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta

from CheersMe.events.models import Event, EventCategory, Organizer
from django.contrib.auth import get_user_model

User = get_user_model()

EVENT_TITLES = [
    "Sunset Rooftop Party", "Live Jazz Night", "Karaoke Friday",
    "Wine & Cheese Evening", "Street Food Festival",
    "Tech Networking Meetup", "Startup Brunch",
    "Afrobeats Night", "Open Mic Poetry",
    "Movie Under The Stars", "Comedy Night",
    "Business Breakfast", "Board Games Meetup",
    "Singles Mixer", "Beach Vibes Party",
    "BBQ Night", "Cocktail Masterclass",
    "Food Truck Rally", "Cultural Dance Night",
    "Quiz & Trivia Night"
]

CITIES = ["Kampala", "Entebbe", "Mukono", "Jinja", "Wakiso"]

IMAGE_KEYWORDS = [
    "concert", "party", "food", "karaoke", "nightlife",
    "festival", "brunch", "crowd", "dj", "dance"
]

class Command(BaseCommand):
    help = "Load 50 sample events with images"

    def handle(self, *args, **kwargs):

        if not EventCategory.objects.exists():
            self.stdout.write("No categories found. Create categories first.")
            return

        # create a dummy organizer if none exists
        if not Organizer.objects.exists():
            user, _ = User.objects.get_or_create(
                email="organizer@cheersme.com",
                defaults={"username": "organizer"}
            )
            organizer = Organizer.objects.create(
                user=user,
                organization_name="CheersMe Events",
                verified=True
            )
        else:
            organizer = Organizer.objects.first()

        categories = list(EventCategory.objects.all())

        for i in range(50):
            title = random.choice(EVENT_TITLES) + f" {i+1}"
            category = random.choice(categories)
            city = random.choice(CITIES)

            start = timezone.now() + timedelta(days=random.randint(1, 60))
            end = start + timedelta(hours=random.randint(2, 6))

            is_free = random.choice([True, False])

            event = Event.objects.create(
                organizer=organizer,
                title=title,
                slug=slugify(title) + f"-{i}",
                description=f"Join us for {title} in {city}. Great vibes, great people and unforgettable moments!",
                category=category,
                venue_name=f"{city} Events Center",
                address="Plot 1, Kampala Road",
                city="Kampala",
                latitude=0.3476,
                longitude=32.5825,
                start_date=start.date(),
                start_time=start.time(),
                end_date=end.date(),
                end_time=end.time(),
                is_free=is_free,
                base_price=0 if is_free else random.randint(10000, 50000),
                total_capacity=200,
                remaining_capacity=200,
                has_food=random.choice([True, False]),
                has_drinks=True
            )

            # Download random image
            keyword = random.choice(IMAGE_KEYWORDS)
            image_url = f"https://source.unsplash.com/800x600/?{keyword},event"

            img_data = requests.get(image_url).content
            event.featured_image.save(
                f"event_{i}.jpg",
                ContentFile(img_data),
                save=True
            )

            self.stdout.write(f"Created: {title}")

        self.stdout.write(self.style.SUCCESS("50 sample events created successfully! 🎉"))
