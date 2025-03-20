import json
from django.core.management.base import BaseCommand
from modelCore.models import Attraction
from modelCore.services import ThemeParksService
from django.core.serializers.json import DjangoJSONEncoder
import uuid

class UUIDEncoder(DjangoJSONEncoder):
    def default(self, obj):
        from uuid import UUID
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)

class Command(BaseCommand):
    help = 'Get detailed information for all attractions and output in JSON format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=str,
            help='Specify an attraction ID to get its details, if not specified all attractions will be returned',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Specify output filename, if not specified output will be printed to console',
        )
        parser.add_argument(
            '--format',
            choices=['json', 'table', 'compare'],
            default='json',
            help='Specify output format: json, table, or compare (compare API and database data)',
        )
        parser.add_argument(
            '--api',
            action='store_true',
            help='Get data directly from API instead of database',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Sync to database after getting API data',
        )

    def handle(self, *args, **options):
        attraction_id = options.get('id')
        output_file = options.get('output')
        output_format = options.get('format')
        use_api = options.get('api')
        sync_to_db = options.get('sync')

        # If compare mode is selected, need to get data from both API and database
        if output_format == 'compare' and attraction_id:
            api_data = ThemeParksService.getAttractionById(attraction_id)
            if not api_data:
                self.stdout.write(self.style.ERROR(f'Attraction with ID {attraction_id} not found in API'))
                return
            
            try:
                db_attraction = Attraction.objects.get(id=attraction_id)
            except Attraction.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Attraction with ID {attraction_id} not found in database, please sync this attraction first'))
                if sync_to_db:
                    try:
                        db_attraction = ThemeParksService.create_attraction_from_entity(api_data)
                        self.stdout.write(self.style.SUCCESS(f'Successfully synced attraction "{api_data.get("name")}" to database'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Sync failed: {e}'))
                        return
                else:
                    return
            
            # Create comparison table
            self.stdout.write(self.style.SUCCESS(f'Comparing API and database data for attraction with ID {attraction_id}'))
            self.stdout.write('{:<15} {:<45} {:<45}'.format('Field', 'API Data', 'Database Data'))
            self.stdout.write('-' * 105)
            
            # Convert API data to more readable format
            api_fields = {
                'id': api_data.get('id'),
                'name': api_data.get('name'),
                'description': api_data.get('meta', {}).get('description', '') if isinstance(api_data.get('meta'), dict) else '',
                'timezone': api_data.get('timezone'),
                'entityType': api_data.get('entityType'),
                'destinationId': api_data.get('destinationId'),
                'attractionType': api_data.get('attractionType'),
                'externalId': api_data.get('externalId'),
                'parentId': api_data.get('parentId'),
                'parkId': api_data.get('parkId'),
                'parkName': api_data.get('park', {}).get('name') if api_data.get('park') else None,
                'longitude': api_data.get('location', {}).get('longitude') if api_data.get('location') else None,
                'latitude': api_data.get('location', {}).get('latitude') if api_data.get('location') else None,
            }
            
            # Database data
            db_fields = {
                'id': str(db_attraction.id),
                'name': db_attraction.name,
                'description': db_attraction.description,
                'timezone': db_attraction.timezone,
                'entity_type': db_attraction.entity_type,
                'destination_id': str(db_attraction.destination_id) if db_attraction.destination_id else None,
                'attraction_type': db_attraction.attraction_type,
                'external_id': db_attraction.external_id,
                'parent_id': str(db_attraction.parent_id) if db_attraction.parent_id else None,
                'park_id': str(db_attraction.park.id) if db_attraction.park else None,
                'park_name': db_attraction.park.name if db_attraction.park else None,
            }
            
            # Compare and display field differences
            for api_key, api_value in api_fields.items():
                db_key = api_key
                # Convert field name format (camelCase -> snake_case)
                if api_key not in ['id', 'name', 'description', 'timezone']:
                    db_key = ''.join(['_' + c.lower() if c.isupper() else c for c in api_key]).lstrip('_')
                
                db_value = db_fields.get(db_key)
                
                # Display field values, mark if different
                match = '✓' if str(api_value) == str(db_value) else '✗'
                self.stdout.write('{:<15} {:<45} {:<45} {}'.format(
                    api_key, 
                    str(api_value)[:42] + '...' if api_value and len(str(api_value)) > 45 else str(api_value), 
                    str(db_value)[:42] + '...' if db_value and len(str(db_value)) > 45 else str(db_value),
                    match
                ))
            
            return

        if attraction_id and use_api:
            # Get detailed information for a single attraction using API
            self.stdout.write(f'Getting details for attraction ID: {attraction_id} from API')
            attraction_data = ThemeParksService.getAttractionById(attraction_id)
            
            if not attraction_data:
                self.stdout.write(self.style.ERROR(f'Attraction with ID {attraction_id} not found in API'))
                return
                
            # If sync to database is needed
            if sync_to_db:
                try:
                    attraction = ThemeParksService.create_attraction_from_entity(attraction_data)
                    self.stdout.write(self.style.SUCCESS(f'Attraction "{attraction.name}" synced to database'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error syncing attraction to database: {e}'))
            
            # Convert to JSON format for output
            if output_format == 'json':
                json_data = json.dumps(attraction_data, indent=4)
                
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(json_data)
                    self.stdout.write(self.style.SUCCESS(f'Attraction API data saved to {output_file}'))
                else:
                    self.stdout.write(json_data)
            else:  # Table format
                self.stdout.write('{:<36} {:<40} {:<20} {:<15}'.format('ID', 'Name', 'Park', 'Attraction Type'))
                self.stdout.write('-' * 115)
                
                self.stdout.write('{:<36} {:<40} {:<20} {:<15}'.format(
                    attraction_data.get('id', 'N/A'),
                    attraction_data.get('name', 'N/A')[:37] + '...' if len(attraction_data.get('name', 'N/A')) > 40 else attraction_data.get('name', 'N/A'),
                    attraction_data.get('park', {}).get('name', 'N/A')[:17] + '...' if len(attraction_data.get('park', {}).get('name', 'N/A')) > 20 else attraction_data.get('park', {}).get('name', 'N/A'),
                    attraction_data.get('attractionType', 'N/A')
                ))
                
        elif attraction_id:
            # Get detailed information for a single attraction from database
            try:
                attraction = Attraction.objects.get(id=attraction_id)
                attractions = [attraction]
                self.stdout.write(f'Getting details for attraction ID: {attraction_id} from database')
            except Attraction.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Attraction with ID {attraction_id} not found in database'))
                return
                
            self.output_attractions(attractions, output_format, output_file)
        elif use_api:
            # Get detailed information for all attractions using API
            self.stdout.write('Getting detailed information for all attractions from API')
            attractions_data = ThemeParksService.getAttractions()
            count = len(attractions_data)
            self.stdout.write(f'Found {count} attractions in API')
            
            # If sync to database is needed
            if sync_to_db:
                synced_count = 0
                for attraction_data in attractions_data:
                    try:
                        ThemeParksService.create_attraction_from_entity(attraction_data)
                        synced_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Error syncing attraction "{attraction_data.get("name", "Unknown")}": {e}'))
                
                self.stdout.write(self.style.SUCCESS(f'Successfully synced {synced_count} attractions to database'))
            
            # Convert to JSON format for output
            if output_format == 'json':
                json_data = json.dumps(attractions_data, indent=4)
                
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(json_data)
                    self.stdout.write(self.style.SUCCESS(f'All attraction API data saved to {output_file}'))
                else:
                    self.stdout.write(json_data)
            else:  # Table format
                self.stdout.write('{:<36} {:<40} {:<20} {:<15}'.format('ID', 'Name', 'Park', 'Attraction Type'))
                self.stdout.write('-' * 115)
                
                for attraction_data in attractions_data:
                    self.stdout.write('{:<36} {:<40} {:<20} {:<15}'.format(
                        attraction_data.get('id', 'N/A'),
                        attraction_data.get('name', 'N/A')[:37] + '...' if len(attraction_data.get('name', 'N/A')) > 40 else attraction_data.get('name', 'N/A'),
                        attraction_data.get('park', {}).get('name', 'N/A')[:17] + '...' if len(attraction_data.get('park', {}).get('name', 'N/A')) > 20 else attraction_data.get('park', {}).get('name', 'N/A'),
                        attraction_data.get('attractionType', 'N/A')
                    ))
        else:
            # Get detailed information for all attractions from database
            attractions = Attraction.objects.all().select_related('park', 'park__destination')
            count = attractions.count()
            self.stdout.write(f'Getting detailed information for all {count} attractions from database')
            
            self.output_attractions(attractions, output_format, output_file)
                
        self.stdout.write(self.style.SUCCESS('Done'))
    
    def output_attractions(self, attractions, output_format, output_file):
        """Output attraction information retrieved from the database"""
        if output_format == 'json':
            # Convert attraction data to JSON format
            attractions_data = []
            for attraction in attractions:
                attraction_data = {
                    'id': attraction.id,
                    'name': attraction.name,
                    'description': attraction.description,
                    'park': {
                        'id': attraction.park.id,
                        'name': attraction.park.name,
                        'destination': {
                            'id': attraction.park.destination.id,
                            'name': attraction.park.destination.name,
                            'slug': attraction.park.destination.slug,
                        }
                    },
                    'timezone': attraction.timezone,
                    'entity_type': attraction.entity_type,
                    'destination_id': attraction.destination_id,
                    'attraction_type': attraction.attraction_type,
                    'external_id': attraction.external_id,
                    'parent_id': attraction.parent_id,
                    'location': {
                        'longitude': attraction.longitude,
                        'latitude': attraction.latitude
                    } if attraction.longitude and attraction.latitude else None,
                    'created_at': attraction.created_at,
                    'updated_at': attraction.updated_at,
                }
                attractions_data.append(attraction_data)

            # Convert data to JSON string
            json_data = json.dumps(attractions_data, indent=4, cls=UUIDEncoder)

            # Output JSON data
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_data)
                self.stdout.write(self.style.SUCCESS(f'Attraction details saved to {output_file}'))
            else:
                self.stdout.write(json_data)
        else:  # Table format
            # Print table header
            self.stdout.write('{:<36} {:<40} {:<20} {:<15}'.format('ID', 'Name', 'Park', 'Attraction Type'))
            self.stdout.write('-' * 115)
            
            # Print information for each attraction
            for attraction in attractions:
                self.stdout.write('{:<36} {:<40} {:<20} {:<15}'.format(
                    str(attraction.id),
                    attraction.name[:37] + '...' if len(attraction.name) > 40 else attraction.name,
                    attraction.park.name[:17] + '...' if len(attraction.park.name) > 20 else attraction.park.name,
                    attraction.attraction_type or 'N/A'
                )) 