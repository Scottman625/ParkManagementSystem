from django.core.management.base import BaseCommand
from modelCore.models import TicketType, Park
from django.db import transaction

class Command(BaseCommand):
    help = 'Setup default ticket types'

    def handle(self, *args, **options):
        self.stdout.write('Starting to setup default ticket types...')
        
        # Ensure park data exists
        parks = Park.objects.all()
        if not parks.exists():
            self.stdout.write(self.style.ERROR('Error: No parks found, please sync park data first'))
            return
        
        # Ticket type definitions
        ticket_types = [
            {
                'name': 'Standard Admission',
                'description': 'Standard admission ticket for general adult visitors. Includes access to all attractions (excluding special events).',
                'price': 49.99,
            },
            {
                'name': 'Family Tickets',
                'description': 'Family package for 2 adults and 2 children (under 12). More economical than buying individual tickets, saving about 15%.',
                'price': 149.99,
            },
            {
                'name': 'Children',
                'description': 'Children\'s ticket for ages 3-11. Children under 3 enter free (must be accompanied by a paying adult).',
                'price': 39.99,
            },
            {
                'name': 'Disabled Guest',
                'description': 'Special ticket for disabled guests, providing special facilities and services. Guests with valid disability documentation can enjoy this discounted price.',
                'price': 29.99,
            },
            {
                'name': 'Senior Citizens (65+)',
                'description': 'Senior ticket for guests aged 65 and above. Valid age verification required. Includes access to all regular facilities.',
                'price': 39.99,
            },
        ]
        
        with transaction.atomic():
            # Create ticket types for each park
            for park in parks:
                # Check if park already has ticket types
                existing_types = TicketType.objects.filter(park=park)
                if existing_types.exists():
                    self.stdout.write(f'Park "{park.name}" already has {existing_types.count()} ticket types, skipping')
                    continue
                
                # Create all ticket types
                for ticket_data in ticket_types:
                    TicketType.objects.create(
                        park=park,
                        name=ticket_data['name'],
                        description=ticket_data['description'],
                        price=ticket_data['price'],
                        is_active=True
                    )
                    self.stdout.write(f'Created ticket type: {ticket_data["name"]} for park "{park.name}"')
        
        self.stdout.write(self.style.SUCCESS('Successfully setup default ticket types!')) 