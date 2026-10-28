from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from django.contrib.auth import get_user_model

# Updated import path to apps.core.models (and removed deleted models)
from apps.core.models import Hobby, Category, Place

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds initial hobbies, categories, and places for ExploreKabankalan"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting database seed for ExploreKabankalan..."))

        # 1. Seed Hobbies
        hobbies_data = [
            {"name": "Billiards", "icon": "ti-ball-8", "description": "Cue sports and pool halls"},
            {"name": "Coffee & Cafe Hopping", "icon": "ti-coffee", "description": "Cozy spots for specialty coffee and casual hangouts"},
            {"name": "Hiking & Eco-Tourism", "icon": "ti-mountain", "description": "Nature trails, caves, and scenic mountain views"},
            {"name": "Karaoke & Nightlife", "icon": "ti-microphone", "description": "KTV bars, live music, and evening entertainment"},
            {"name": "Photography", "icon": "ti-camera", "description": "Picturesque landscapes, heritage spots, and aesthetic spots"},
            {"name": "Dining & Foodie", "icon": "ti-utensils", "description": "Local delicacies, chicken inasal, and dining spots"},
        ]

        hobby_instances = {}
        for h_data in hobbies_data:
            hobby, created = Hobby.objects.get_or_create(
                slug=slugify(h_data["name"]),
                defaults={
                    "name": h_data["name"],
                    "icon": h_data["icon"],
                    "description": h_data["description"]
                }
            )
            hobby_instances[h_data["name"]] = hobby

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(hobby_instances)} Hobbies."))

        # 2. Seed Categories
        categories_data = [
            {"name": "Food & Dining", "description": "Restaurants, cafes, and local food spots"},
            {"name": "Sports & Recreation", "description": "Billiard halls, gyms, and sports venues"},
            {"name": "Tourist Attraction", "description": "Natural wonders, parks, and cultural sites"},
            {"name": "Accommodation", "description": "Hotels, inns, and staycations in Kabankalan"},
            {"name": "Transport Hub", "description": "Bus terminals, jeepney terminals, and transport stops"},
        ]

        category_instances = {}
        for c_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=c_data["name"],
                defaults={"description": c_data["description"]}
            )
            category_instances[c_data["name"]] = category

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(category_instances)} Categories."))

        # 3. Seed Sample Kabankalan Places
        places_data = [
            {
                "title": "Mag-Aso Falls",
                "category": category_instances["Tourist Attraction"],
                "hobbies": [hobby_instances["Hiking & Eco-Tourism"], hobby_instances["Photography"]],
                "description": "Famous natural waterfall surrounded by lush green landscapes and turquoise natural swimming pools.",
                "address": "Sitio Mag-aso, Barangay Oringao, Kabankalan City",
                "barangay": "Barangay Oringao",
                "latitude": 9.923400,
                "longitude": 122.861100,
                "operating_hours": "Mon-Sun: 7:00 AM - 5:00 PM",
                "contact_number": "+63 912 345 6789",
                "ai_keywords": "waterfall, swimming, nature, eco-tourism, hiking, scenic view, picnic, oringao",
                "is_verified": True
            },
            {
                "title": "Balicaocao Highland Resort",
                "category": category_instances["Tourist Attraction"],
                "hobbies": [hobby_instances["Photography"], hobby_instances["Coffee & Cafe Hopping"], hobby_instances["Hiking & Eco-Tourism"]],
                "description": "Highland resort sitting 500 feet above sea level offering panoramic views of Kabankalan and nearby towns.",
                "address": "Barangay Orong, Kabankalan City",
                "barangay": "Barangay Orong",
                "latitude": 9.967800,
                "longitude": 122.845000,
                "operating_hours": "Mon-Sun: 8:00 AM - 7:00 PM",
                "contact_number": "+63 998 765 4321",
                "ai_keywords": "highland, mountain view, resort, swimming pool, breeze, sunset photo spot, relaxing",
                "is_verified": True
            },
            {
                "title": "Cue & Break Billiard Center",
                "category": category_instances["Sports & Recreation"],
                "hobbies": [hobby_instances["Billiards"], hobby_instances["Karaoke & Nightlife"]],
                "description": "Spacious billiard hall located near the city center equipped with standard pool tables and refreshments.",
                "address": "Guanzon Street, Barangay 1, Kabankalan City",
                "barangay": "Barangay 1",
                "latitude": 9.988200,
                "longitude": 122.815500,
                "operating_hours": "Mon-Sun: 1:00 PM - 11:00 PM",
                "contact_number": "+63 930 111 2233",
                "ai_keywords": "billiards, pool hall, cue sports, aircon, barkada hangout, night activity, play pool tonight",
                "is_verified": True
            },
            {
                "title": "Central City Cafe & Lounge",
                "category": category_instances["Food & Dining"],
                "hobbies": [hobby_instances["Coffee & Cafe Hopping"], hobby_instances["Dining & Foodie"]],
                "description": "Modern cafe offering brewed coffee, cold drinks, pasta, and pastries. Great environment for students and workers.",
                "address": "Near City Public Plaza, Barangay 2, Kabankalan City",
                "barangay": "Barangay 2",
                "latitude": 9.989100,
                "longitude": 122.816200,
                "operating_hours": "Mon-Sat: 9:00 AM - 9:00 PM",
                "contact_number": "+63 945 999 8877",
                "ai_keywords": "coffee, wifi, aircon, study spot, espresso, pastries, snacks, central kabankalan",
                "is_verified": True
            }
        ]

        for p_data in places_data:
            assigned_hobbies = p_data.pop("hobbies")
            place, created = Place.objects.get_or_create(
                title=p_data["title"],
                defaults=p_data
            )
            place.hobbies.set(assigned_hobbies)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(places_data)} Places in Kabankalan City."))
        self.stdout.write(self.style.SUCCESS("All seed data successfully injected!"))