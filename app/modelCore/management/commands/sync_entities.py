from django.core.management.base import BaseCommand
from modelCore.services import ThemeParksService
from modelCore.models import Destination, Park, Attraction
from django.db import transaction
import time

class Command(BaseCommand):
    help = 'Sync destinations and parks data from ThemeParks API using Database and entity mode'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync all data, ignore cache',
        )
        parser.add_argument(
            '--entity-id',
            type=str,
            help='Only sync entity with specified ID',
        )
        parser.add_argument(
            '--entity-type',
            type=str,
            choices=['destination', 'park', 'attraction'],
            help='Specify entity type to sync (destination, park or attraction)',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        entity_id = options.get('entity_id')
        entity_type = options.get('entity_type')
        
        start_time = time.time()
        
        if entity_id and entity_type:
            # Sync specific entity
            self.sync_specific_entity(entity_type, entity_id)
        elif entity_type:
            # Sync all entities of specific type
            self.sync_entity_type(entity_type, force)
        else:
            # Sync all entities
            self.sync_all_entities(force)
        
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f'Sync completed, took {elapsed_time:.2f} seconds'))
    
    def sync_specific_entity(self, entity_type, entity_id):
        """Sync specific entity"""
        self.stdout.write(f'Syncing {entity_type} ID: {entity_id}')
        
        if entity_type == 'destination':
            entity_data = ThemeParksService.getDestinationById(entity_id)
            if entity_data:
                try:
                    destination = ThemeParksService.create_destination_from_entity(entity_data)
                    self.stdout.write(self.style.SUCCESS(f'Destination "{destination.name}" synced'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error syncing destination: {e}'))
            else:
                self.stdout.write(self.style.ERROR(f'Destination with ID {entity_id} not found'))
                
        elif entity_type == 'park':
            entity_data = ThemeParksService.getEntityById(entity_id)
            if entity_data:
                try:
                    park = ThemeParksService.create_park_from_entity(entity_data)
                    self.stdout.write(self.style.SUCCESS(f'Park "{park.name}" synced'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error syncing park: {e}'))
            else:
                self.stdout.write(self.style.ERROR(f'Park with ID {entity_id} not found'))

        elif entity_type == 'attraction':
            entity_data = ThemeParksService.getAttractionById(entity_id)
            if entity_data:
                try:
                    attraction = ThemeParksService.create_attraction_from_entity(entity_data)
                    self.stdout.write(self.style.SUCCESS(f'Attraction "{attraction.name}" synced'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error syncing attraction: {e}'))
            else:
                self.stdout.write(self.style.ERROR(f'Attraction with ID {entity_id} not found'))
    
    def sync_entity_type(self, entity_type, force=False):
        """Sync all entities of specific type"""
        if entity_type == 'destination':
            self.sync_destinations(force)
        elif entity_type == 'park':
            self.sync_parks(force)
        elif entity_type == 'attraction':
            self.sync_attractions(force)
    
    def sync_all_entities(self, force=False):
        """Sync all entities"""
        self.stdout.write('Starting to sync all entities')
        
        # Sync destinations first
        destinations = self.sync_destinations(force)
        
        # Then sync parks
        parks = self.sync_parks(force)
        
        # Finally sync attractions
        self.sync_attractions(force)
    
    def sync_destinations(self, force=False):
        """Sync all destinations"""
        self.stdout.write('Syncing destinations...')
        
        try:
            # Get all destination data
            destinations_data = ThemeParksService.get_all_destinations()
            
            destinations = []
            with transaction.atomic():
                for dest_data in destinations_data:
                    try:
                        destination = ThemeParksService.create_destination_from_entity(dest_data)
                        destinations.append(destination)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Error syncing destination "{dest_data.get("name", "Unknown")}": {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'Successfully synced {len(destinations)} destinations'))
            return destinations
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error syncing destinations: {e}'))
            return []
    
    def sync_parks(self, force=False):
        """Sync all parks"""
        self.stdout.write('Syncing parks...')
        
        try:
            # Get all park data
            parks_data = ThemeParksService.getEntities()
            
            parks = []
            with transaction.atomic():
                for park_data in parks_data:
                    try:
                        park = ThemeParksService.create_park_from_entity(park_data)
                        parks.append(park)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Error syncing park "{park_data.get("name", "Unknown")}": {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'Successfully synced {len(parks)} parks'))
            return parks
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error syncing parks: {e}'))
            return []
            
    def sync_attractions(self, force=False):
        """Sync all attractions"""
        self.stdout.write('Syncing attractions...')
        
        try:
            # Get all attraction data
            attractions_data = ThemeParksService.getAttractions()
            
            attractions = []
            with transaction.atomic():
                for attraction_data in attractions_data:
                    try:
                        attraction = ThemeParksService.create_attraction_from_entity(attraction_data)
                        attractions.append(attraction)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Error syncing attraction "{attraction_data.get("name", "Unknown")}": {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'Successfully synced {len(attractions)} attractions'))
            return attractions
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error syncing attractions: {e}'))
            return [] 