import requests
import uuid
from .models import Destination, Park, Attraction
from django.db import transaction

class ThemeParksService:
    """Theme Parks API Service Class"""
    
    BASE_URL = "https://api.themeparks.wiki/v1"

    @staticmethod
    def create_destination_from_entity(entity):
        """
        Create or update a Destination instance from entity data returned by API
        
        Args:
            entity (dict): Destination data returned by API
            
        Returns:
            Destination: Created or updated Destination instance
        """
        from .models import Destination
        
        # Extract necessary data from entity
        destination_id = entity.get('id')
        if not destination_id:
            raise ValueError("Destination ID cannot be empty")
        
        # Create or update Destination instance
        destination, created = Destination.objects.update_or_create(
            id=uuid.UUID(destination_id),
            defaults={
                'name': entity.get('name', ''),
                'slug': entity.get('slug', ''),
            }
        )
        
        return destination

    @staticmethod
    def create_park_from_entity(entity, destination=None):
        """
        Create or update a Park instance from entity data returned by API
        
        Args:
            entity (dict): Park data returned by API
            destination (Destination, optional): Corresponding destination instance, if None will be retrieved from entity
            
        Returns:
            Park: Created or updated Park instance
        """
        from .models import Park
        
        # Extract necessary data from entity
        park_id = entity.get('id')
        if not park_id:
            raise ValueError("Park ID cannot be empty")
        
        # If destination instance is not provided, try to get destination info from entity
        if destination is None and 'destination' in entity:
            destination_data = entity.get('destination')
            destination = ThemeParksService.create_destination_from_entity(destination_data)
        
        if destination is None:
            raise ValueError("Missing destination information")
        
        # Create or update Park instance
        park, created = Park.objects.update_or_create(
            id=uuid.UUID(park_id),
            defaults={
                'name': entity.get('name', ''),
                'destination': destination,
            }
        )
        
        return park

    @staticmethod
    def create_attraction_from_entity(entity, park=None):
        """
        Create or update an Attraction instance from entity data returned by API
        
        Args:
            entity (dict): Attraction data returned by API
            park (Park, optional): Corresponding park instance, if None will be retrieved from entity
            
        Returns:
            Attraction: Created or updated Attraction instance
        """
        from .models import Attraction
        
        # Extract necessary data from entity
        attraction_id = entity.get('id')
        if not attraction_id:
            raise ValueError("Attraction ID cannot be empty")
        
        # If park instance is not provided, try to get park info from entity
        if park is None and 'park' in entity:
            park_data = entity.get('park')
            
            # Check if park data includes destination information
            if 'destination' not in entity:
                raise ValueError("Missing destination information")
            
            # First create or get destination
            destination_data = entity.get('destination')
            destination = ThemeParksService.create_destination_from_entity(destination_data)
            
            # Create or get park
            park = ThemeParksService.create_park_from_entity(park_data, destination)
        
        if park is None:
            # Try to get park from parentId
            parent_id = entity.get('parentId')
            if parent_id:
                park_data = ThemeParksService.getEntityById(parent_id)
                if park_data:
                    # Create or get destination and park
                    destination_data = park_data.get('destination')
                    if destination_data:
                        destination = ThemeParksService.create_destination_from_entity(destination_data)
                        park = ThemeParksService.create_park_from_entity(park_data, destination)
        
        if park is None:
            raise ValueError("Missing park information")
        
        # Get description
        description = ''
        if 'meta' in entity and entity['meta'] and 'description' in entity['meta']:
            description = entity['meta']['description']
        
        # Get location information
        longitude = None
        latitude = None
        if 'location' in entity:
            location = entity.get('location', {})
            longitude = location.get('longitude')
            latitude = location.get('latitude')
        
        # Create or update Attraction instance
        attraction, created = Attraction.objects.update_or_create(
            id=uuid.UUID(attraction_id),
            defaults={
                'name': entity.get('name', ''),
                'park': park,
                'description': description,
                # Ensure field names match API keys exactly
                'timezone': entity.get('timezone'),
                'entity_type': entity.get('entityType'),
                'destination_id': uuid.UUID(entity.get('destinationId')) if entity.get('destinationId') else None,
                'attraction_type': entity.get('attractionType'),
                'external_id': entity.get('externalId'),
                'parent_id': uuid.UUID(entity.get('parentId')) if entity.get('parentId') else None,
                # Location information
                'longitude': longitude,
                'latitude': latitude,
            }
        )
        
        return attraction
        
    @staticmethod
    def sync_destinations():
        """
        Synchronize destination and park data from ThemeParks API to database
        
        Returns:
            tuple: (bool, str) - Whether synchronization was successful, and success or error message
        """
        try:
            # Get API data
            response = requests.get(f"{ThemeParksService.BASE_URL}/destinations")
            response.raise_for_status()
            destinations_data = response.json().get('destinations', [])

            with transaction.atomic():
                # Iterate through all destinations
                for dest_data in destinations_data:
                    # Create or update destination
                    destination, created = Destination.objects.update_or_create(
                        id=uuid.UUID(dest_data['id']),
                        defaults={
                            'name': dest_data['name'],
                            'slug': dest_data['slug']
                        }
                    )

                    # Process all parks for this destination
                    for park_data in dest_data.get('parks', []):
                        park, created = Park.objects.update_or_create(
                            id=uuid.UUID(park_data['id']),
                            defaults={
                                'name': park_data['name'],
                                'destination': destination
                            }
                        )

            return True, "Data synchronized successfully"
        except requests.RequestException as e:
            return False, f"API request error: {str(e)}"
        except Exception as e:
            return False, f"Error during synchronization: {str(e)}"
    
    @staticmethod
    def fetch_destinations():
        """
        Get all destination information from ThemeParks API
        
        Returns:
            list: List of destinations
        """
        try:
            response = requests.get(f"{ThemeParksService.BASE_URL}/destinations")
            response.raise_for_status()
            return response.json().get('destinations', [])
        except Exception as e:
            print(f"Error fetching destinations: {e}")
            return []
    
    @staticmethod
    def get_all_destinations():
        """
        Get all destination information from ThemeParks API
        
        Returns:
            list: List of destinations
        """
        return ThemeParksService.fetch_destinations()
    
    @staticmethod
    def getEntities():
        """
        Get all park information from ThemeParks API
        
        Returns:
            list: List of parks
        """
        try:
            # Get all destinations
            destinations = ThemeParksService.fetch_destinations()
            
            # Collect all parks
            parks = []
            for dest in destinations:
                for park in dest.get('parks', []):
                    # Add destination information to park data
                    park['destination'] = {
                        'id': dest.get('id'),
                        'name': dest.get('name'),
                        'slug': dest.get('slug')
                    }
                    parks.append(park)
            
            return parks
        except Exception as e:
            print(f"Error fetching parks: {e}")
            return []
    
    @staticmethod
    def get_all_parks():
        """
        Get all park information from ThemeParks API (compatible with old method name)
        
        Returns:
            list: List of parks
        """
        return ThemeParksService.getEntities()
    
    @staticmethod
    def getEntityById(entity_id):
        """
        Get information about a specific park from ThemeParks API
        
        Args:
            entity_id (str): Park ID
            
        Returns:
            dict: Park information
        """
        try:
            # Get all destinations
            destinations = ThemeParksService.fetch_destinations()
            
            # Find specific park
            for dest in destinations:
                for park in dest.get('parks', []):
                    if park.get('id') == str(entity_id):
                        # Add destination information to park data
                        park['destination'] = {
                            'id': dest.get('id'),
                            'name': dest.get('name'),
                            'slug': dest.get('slug')
                        }
                        return park
            
            return None
        except Exception as e:
            print(f"Error fetching park: {e}")
            return None
    
    @staticmethod
    def get_park_by_id(park_id):
        """
        Get information about a specific park from ThemeParks API (compatible with old method name)
        
        Args:
            park_id (str): Park ID
            
        Returns:
            dict: Park information
        """
        return ThemeParksService.getEntityById(park_id)
    
    @staticmethod
    def getDestinationById(destination_id):
        """
        Get information about a specific destination from ThemeParks API
        
        Args:
            destination_id (str): Destination ID
            
        Returns:
            dict: Destination information
        """
        try:
            # Get all destinations
            destinations = ThemeParksService.fetch_destinations()
            
            # Find specific destination
            for dest in destinations:
                if dest.get('id') == str(destination_id):
                    return dest
            
            return None
        except Exception as e:
            print(f"Error fetching destination: {e}")
            return None
    
    @staticmethod
    def get_destination_by_id(destination_id):
        """
        Get information about a specific destination from ThemeParks API (compatible with old method name)
        
        Args:
            destination_id (str): Destination ID
            
        Returns:
            dict: Destination information
        """
        return ThemeParksService.getDestinationById(destination_id)
    
    @staticmethod
    def findEntities(filter_obj=None):
        """
        Get parks from ThemeParks API that match the conditions
        
        Args:
            filter_obj (dict, optional): Filter conditions
            
        Returns:
            list: List of parks matching conditions
        """
        try:
            # Get all parks
            parks = ThemeParksService.getEntities()
            
            # If no filter conditions, return all parks
            if not filter_obj:
                return parks
            
            # Apply filter conditions
            filtered_parks = []
            for park in parks:
                match = True
                for key, value in filter_obj.items():
                    # Handle nested attributes, e.g. 'destination.id'
                    if '.' in key:
                        parts = key.split('.')
                        park_value = park
                        for part in parts:
                            if part in park_value:
                                park_value = park_value[part]
                            else:
                                park_value = None
                                break
                    else:
                        park_value = park.get(key)
                    
                    # Check if value matches
                    if park_value is None or str(park_value) != str(value):
                        match = False
                        break
                
                if match:
                    filtered_parks.append(park)
            
            return filtered_parks
        except Exception as e:
            print(f"Error finding parks: {e}")
            return []
    
    @staticmethod
    def get_parks_by_destination(destination_id):
        """
        Get all parks for a specific destination from ThemeParks API (compatible with old method name)
        
        Args:
            destination_id (str): Destination ID
            
        Returns:
            list: List of parks
        """
        return ThemeParksService.findEntities({'destination.id': destination_id})
        
    @staticmethod
    def getAttractions():
        """
        Get all attraction information from ThemeParks API
        
        Returns:
            list: List of attractions
        """
        try:
            # Get all parks
            parks = ThemeParksService.getEntities()
            
            # Get attractions for each park
            attractions = []
            for park in parks:
                park_id = park.get('id')
                
                # Try to get attractions for this park
                try:
                    response = requests.get(f"{ThemeParksService.BASE_URL}/entity/{park_id}/children")
                    response.raise_for_status()
                    
                    # Filter entities of type ATTRACTION
                    children = response.json().get('children', [])
                    for attraction in children:
                        if attraction.get('entityType') == 'ATTRACTION':
                            # Add park and destination information to attraction data
                            attraction['park'] = {
                                'id': park.get('id'),
                                'name': park.get('name')
                            }
                            attraction['destination'] = park.get('destination')
                            attractions.append(attraction)
                except Exception as e:
                    print(f"Error fetching attractions for park ID {park_id}: {e}")
                    continue
                    
            return attractions
        except Exception as e:
            print(f"Error fetching attractions: {e}")
            return []
            
    @staticmethod
    def getAttractionById(attraction_id):
        """
        Get information about a specific attraction from ThemeParks API
        
        Args:
            attraction_id (str): Attraction ID
            
        Returns:
            dict: Attraction information
        """
        try:
            # Directly get entity information
            response = requests.get(f"{ThemeParksService.BASE_URL}/entity/{attraction_id}")
            
            if response.status_code == 200:
                entity_data = response.json()
                
                # Check if it's an attraction type
                if entity_data.get('entityType') == 'ATTRACTION':
                    # Find the park this attraction belongs to
                    try:
                        parent_id = entity_data.get('parentId')
                        parent_data = ThemeParksService.getEntityById(parent_id)
                        
                        if parent_data:
                            # Add park and destination information
                            entity_data['park'] = {
                                'id': parent_data.get('id'),
                                'name': parent_data.get('name')
                            }
                            entity_data['destination'] = parent_data.get('destination')
                    except Exception as e:
                        print(f"Error fetching attraction's parent entity: {e}")
                    
                    return entity_data
            
            # If direct request fails, try to find in all attractions
            attractions = ThemeParksService.getAttractions()
            for attraction in attractions:
                if attraction.get('id') == str(attraction_id):
                    return attraction
                    
            return None
        except Exception as e:
            print(f"Error fetching attraction: {e}")
            return None
            
    @staticmethod
    def get_attractions_by_park(park_id):
        """
        Get all attractions for a specific park from ThemeParks API
        
        Args:
            park_id (str): Park ID
            
        Returns:
            list: List of attractions
        """
        try:
            response = requests.get(f"{ThemeParksService.BASE_URL}/entity/{park_id}/children")
            
            if response.status_code == 200:
                children = response.json().get('children', [])
                
                # Filter entities of type ATTRACTION
                attractions = []
                park_data = ThemeParksService.getEntityById(park_id)
                
                for attraction in children:
                    if attraction.get('entityType') == 'ATTRACTION':
                        # Add park and destination information
                        if park_data:
                            attraction['park'] = {
                                'id': park_data.get('id'),
                                'name': park_data.get('name')
                            }
                            attraction['destination'] = park_data.get('destination')
                        attractions.append(attraction)
                
                return attractions
            
            return []
        except Exception as e:
            print(f"Error fetching park attractions: {e}")
            return [] 