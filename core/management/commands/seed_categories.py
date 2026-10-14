from django.core.management.base import BaseCommand
from django.utils.text import slugify

from core.models import ServiceCategory

CATEGORIES = [
    ("Electrician", "lightning-charge", "Electrical repairs, wiring and installations."),
    ("Plumber", "droplet", "Pipe repairs, fittings and water systems."),
    ("Carpenter", "hammer", "Woodwork, furniture and home fittings."),
    ("Painter", "paint-bucket", "Fresh colours and finishes for your space."),
    ("Mason", "bricks", "Brickwork, repairs and structural craftsmanship."),
    ("Cleaner", "stars", "Cleaning for homes, offices and shared spaces."),
    ("Mechanic", "gear", "Vehicle maintenance and mechanical repairs."),
    ("AC Technician", "snow", "Cooling system installation and maintenance."),
    ("Appliance Repair Technician", "plug", "Repair and maintenance of home appliances."),
    ("Welder", "fire", "Metal fabrication and welding work."),
    ("Gardener", "flower1", "Care for gardens and green spaces."),
    ("Driver", "car-front", "Professional driving services."),
    ("Helper", "person-arms-up", "An extra pair of hands for everyday tasks."),
    ("General Labourer", "tools", "Local general work and practical assistance."),
    ("Construction Worker", "building", "Support for construction and renovation."),
    ("Home Maintenance Worker", "house-gear", "Keep your home in good working order."),
    ("Other Professionals", "briefcase", "Specialist local services and skills."),
]


class Command(BaseCommand):
    help = "Create common service categories without demo accounts."

    def handle(self, *args, **options):
        for name, icon, description in CATEGORIES:
            ServiceCategory.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "icon": icon, "description": description},
            )
        self.stdout.write(self.style.SUCCESS("Service categories are ready."))
