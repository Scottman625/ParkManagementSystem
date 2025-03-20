import requests
import uuid
from .models import Destination, Park, Attraction
from django.db import transaction

class ThemeParksService:
    """主題公園 API 服務類"""
    
    BASE_URL = "https://api.themeparks.wiki/v1"

    @staticmethod
    def create_destination_from_entity(entity):
        """
        從 API 返回的 entity 數據創建或更新 Destination 實例
        
        Args:
            entity (dict): API 返回的目的地數據
            
        Returns:
            Destination: 創建或更新的 Destination 實例
        """
        from .models import Destination
        
        # 從 entity 中提取必要的數據
        destination_id = entity.get('id')
        if not destination_id:
            raise ValueError("目的地 ID 不能為空")
        
        # 創建或更新 Destination 實例
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
        從 API 返回的 entity 數據創建或更新 Park 實例
        
        Args:
            entity (dict): API 返回的公園數據
            destination (Destination, optional): 對應的目的地實例，如果為 None 則從 entity 中獲取
            
        Returns:
            Park: 創建或更新的 Park 實例
        """
        from .models import Park
        
        # 從 entity 中提取必要的數據
        park_id = entity.get('id')
        if not park_id:
            raise ValueError("公園 ID 不能為空")
        
        # 如果沒有提供 destination 實例，則嘗試從 entity 中獲取目的地信息
        if destination is None and 'destination' in entity:
            destination_data = entity.get('destination')
            destination = ThemeParksService.create_destination_from_entity(destination_data)
        
        if destination is None:
            raise ValueError("缺少目的地信息")
        
        # 創建或更新 Park 實例
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
        從 API 返回的 entity 數據創建或更新 Attraction 實例
        
        Args:
            entity (dict): API 返回的吸引設施數據
            park (Park, optional): 對應的公園實例，如果為 None 則從 entity 中獲取
            
        Returns:
            Attraction: 創建或更新的 Attraction 實例
        """
        from .models import Attraction
        
        # 從 entity 中提取必要的數據
        attraction_id = entity.get('id')
        if not attraction_id:
            raise ValueError("吸引設施 ID 不能為空")
        
        # 如果沒有提供 park 實例，則嘗試從 entity 中獲取公園信息
        if park is None and 'park' in entity:
            park_data = entity.get('park')
            
            # 檢查公園數據中是否包含目的地信息
            if 'destination' not in entity:
                raise ValueError("缺少目的地信息")
            
            # 先創建或獲取目的地
            destination_data = entity.get('destination')
            destination = ThemeParksService.create_destination_from_entity(destination_data)
            
            # 創建或獲取公園
            park = ThemeParksService.create_park_from_entity(park_data, destination)
        
        if park is None:
            # 嘗試從 parentId 獲取公園
            parent_id = entity.get('parentId')
            if parent_id:
                park_data = ThemeParksService.getEntityById(parent_id)
                if park_data:
                    # 創建或獲取目的地和公園
                    destination_data = park_data.get('destination')
                    if destination_data:
                        destination = ThemeParksService.create_destination_from_entity(destination_data)
                        park = ThemeParksService.create_park_from_entity(park_data, destination)
        
        if park is None:
            raise ValueError("缺少公園信息")
        
        # 獲取描述
        description = ''
        if 'meta' in entity and entity['meta'] and 'description' in entity['meta']:
            description = entity['meta']['description']
        
        # 獲取位置信息
        longitude = None
        latitude = None
        if 'location' in entity:
            location = entity.get('location', {})
            longitude = location.get('longitude')
            latitude = location.get('latitude')
        
        # 創建或更新 Attraction 實例
        attraction, created = Attraction.objects.update_or_create(
            id=uuid.UUID(attraction_id),
            defaults={
                'name': entity.get('name', ''),
                'park': park,
                'description': description,
                # 確保字段名稱與API返回的鍵完全匹配
                'timezone': entity.get('timezone'),
                'entity_type': entity.get('entityType'),
                'destination_id': uuid.UUID(entity.get('destinationId')) if entity.get('destinationId') else None,
                'attraction_type': entity.get('attractionType'),
                'external_id': entity.get('externalId'),
                'parent_id': uuid.UUID(entity.get('parentId')) if entity.get('parentId') else None,
                # 位置資訊
                'longitude': longitude,
                'latitude': latitude,
            }
        )
        
        return attraction
        
    @staticmethod
    def sync_destinations():
        """
        從 ThemeParks API 同步目的地和公園數據到數據庫
        
        Returns:
            tuple: (bool, str) - 同步是否成功，以及成功或錯誤消息
        """
        try:
            # 獲取 API 數據
            response = requests.get(f"{ThemeParksService.BASE_URL}/destinations")
            response.raise_for_status()
            destinations_data = response.json().get('destinations', [])

            with transaction.atomic():
                # 遍歷所有目的地
                for dest_data in destinations_data:
                    # 創建或更新目的地
                    destination, created = Destination.objects.update_or_create(
                        id=uuid.UUID(dest_data['id']),
                        defaults={
                            'name': dest_data['name'],
                            'slug': dest_data['slug']
                        }
                    )

                    # 處理該目的地的所有公園
                    for park_data in dest_data.get('parks', []):
                        park, created = Park.objects.update_or_create(
                            id=uuid.UUID(park_data['id']),
                            defaults={
                                'name': park_data['name'],
                                'destination': destination
                            }
                        )

            return True, "數據同步成功"
        except requests.RequestException as e:
            return False, f"API 請求錯誤: {str(e)}"
        except Exception as e:
            return False, f"同步過程中發生錯誤: {str(e)}"
    
    @staticmethod
    def fetch_destinations():
        """
        從 ThemeParks API 獲取所有目的地信息
        
        Returns:
            list: 目的地列表
        """
        try:
            response = requests.get(f"{ThemeParksService.BASE_URL}/destinations")
            response.raise_for_status()
            return response.json().get('destinations', [])
        except Exception as e:
            print(f"獲取目的地時出錯: {e}")
            return []
    
    @staticmethod
    def get_all_destinations():
        """
        從 ThemeParks API 獲取所有目的地信息
        
        Returns:
            list: 目的地列表
        """
        return ThemeParksService.fetch_destinations()
    
    @staticmethod
    def getEntities():
        """
        從 ThemeParks API 獲取所有公園信息
        
        Returns:
            list: 公園列表
        """
        try:
            # 獲取所有目的地
            destinations = ThemeParksService.fetch_destinations()
            
            # 收集所有公園
            parks = []
            for dest in destinations:
                for park in dest.get('parks', []):
                    # 添加目的地信息到公園數據中
                    park['destination'] = {
                        'id': dest.get('id'),
                        'name': dest.get('name'),
                        'slug': dest.get('slug')
                    }
                    parks.append(park)
            
            return parks
        except Exception as e:
            print(f"獲取公園時出錯: {e}")
            return []
    
    @staticmethod
    def get_all_parks():
        """
        從 ThemeParks API 獲取所有公園信息（兼容舊的方法名）
        
        Returns:
            list: 公園列表
        """
        return ThemeParksService.getEntities()
    
    @staticmethod
    def getEntityById(entity_id):
        """
        從 ThemeParks API 獲取特定公園信息
        
        Args:
            entity_id (str): 公園 ID
            
        Returns:
            dict: 公園信息
        """
        try:
            # 獲取所有目的地
            destinations = ThemeParksService.fetch_destinations()
            
            # 查找特定公園
            for dest in destinations:
                for park in dest.get('parks', []):
                    if park.get('id') == str(entity_id):
                        # 添加目的地信息到公園數據中
                        park['destination'] = {
                            'id': dest.get('id'),
                            'name': dest.get('name'),
                            'slug': dest.get('slug')
                        }
                        return park
            
            return None
        except Exception as e:
            print(f"獲取公園時出錯: {e}")
            return None
    
    @staticmethod
    def get_park_by_id(park_id):
        """
        從 ThemeParks API 獲取特定公園信息（兼容舊的方法名）
        
        Args:
            park_id (str): 公園 ID
            
        Returns:
            dict: 公園信息
        """
        return ThemeParksService.getEntityById(park_id)
    
    @staticmethod
    def getDestinationById(destination_id):
        """
        從 ThemeParks API 獲取特定目的地信息
        
        Args:
            destination_id (str): 目的地 ID
            
        Returns:
            dict: 目的地信息
        """
        try:
            # 獲取所有目的地
            destinations = ThemeParksService.fetch_destinations()
            
            # 查找特定目的地
            for dest in destinations:
                if dest.get('id') == str(destination_id):
                    return dest
            
            return None
        except Exception as e:
            print(f"獲取目的地時出錯: {e}")
            return None
    
    @staticmethod
    def get_destination_by_id(destination_id):
        """
        從 ThemeParks API 獲取特定目的地信息（兼容舊的方法名）
        
        Args:
            destination_id (str): 目的地 ID
            
        Returns:
            dict: 目的地信息
        """
        return ThemeParksService.getDestinationById(destination_id)
    
    @staticmethod
    def findEntities(filter_obj=None):
        """
        從 ThemeParks API 獲取符合條件的公園
        
        Args:
            filter_obj (dict, optional): 過濾條件
            
        Returns:
            list: 符合條件的公園列表
        """
        try:
            # 獲取所有公園
            parks = ThemeParksService.getEntities()
            
            # 如果沒有過濾條件，則返回所有公園
            if not filter_obj:
                return parks
            
            # 應用過濾條件
            filtered_parks = []
            for park in parks:
                match = True
                for key, value in filter_obj.items():
                    # 處理嵌套屬性，例如 'destination.id'
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
                    
                    # 檢查值是否匹配
                    if park_value is None or str(park_value) != str(value):
                        match = False
                        break
                
                if match:
                    filtered_parks.append(park)
            
            return filtered_parks
        except Exception as e:
            print(f"查找公園時出錯: {e}")
            return []
    
    @staticmethod
    def get_parks_by_destination(destination_id):
        """
        從 ThemeParks API 獲取特定目的地的所有公園（兼容舊的方法名）
        
        Args:
            destination_id (str): 目的地 ID
            
        Returns:
            list: 公園列表
        """
        return ThemeParksService.findEntities({'destination.id': destination_id})
        
    @staticmethod
    def getAttractions():
        """
        從 ThemeParks API 獲取所有吸引設施信息
        
        Returns:
            list: 吸引設施列表
        """
        try:
            # 獲取所有公園
            parks = ThemeParksService.getEntities()
            
            # 獲取每個公園的吸引設施
            attractions = []
            for park in parks:
                park_id = park.get('id')
                
                # 嘗試獲取此公園的吸引設施
                try:
                    response = requests.get(f"{ThemeParksService.BASE_URL}/entity/{park_id}/children")
                    response.raise_for_status()
                    
                    # 過濾出類型為 ATTRACTION 的實體
                    children = response.json().get('children', [])
                    for attraction in children:
                        if attraction.get('entityType') == 'ATTRACTION':
                            # 添加公園和目的地信息到吸引設施數據中
                            attraction['park'] = {
                                'id': park.get('id'),
                                'name': park.get('name')
                            }
                            attraction['destination'] = park.get('destination')
                            attractions.append(attraction)
                except Exception as e:
                    print(f"獲取公園 ID {park_id} 的吸引設施時出錯: {e}")
                    continue
                    
            return attractions
        except Exception as e:
            print(f"獲取吸引設施時出錯: {e}")
            return []
            
    @staticmethod
    def getAttractionById(attraction_id):
        """
        從 ThemeParks API 獲取特定吸引設施信息
        
        Args:
            attraction_id (str): 吸引設施 ID
            
        Returns:
            dict: 吸引設施信息
        """
        try:
            # 直接獲取實體信息
            response = requests.get(f"{ThemeParksService.BASE_URL}/entity/{attraction_id}")
            
            if response.status_code == 200:
                entity_data = response.json()
                
                # 檢查是否為吸引設施類型
                if entity_data.get('entityType') == 'ATTRACTION':
                    # 尋找此吸引設施所屬的公園
                    try:
                        parent_id = entity_data.get('parentId')
                        parent_data = ThemeParksService.getEntityById(parent_id)
                        
                        if parent_data:
                            # 添加公園和目的地信息
                            entity_data['park'] = {
                                'id': parent_data.get('id'),
                                'name': parent_data.get('name')
                            }
                            entity_data['destination'] = parent_data.get('destination')
                    except Exception as e:
                        print(f"獲取吸引設施父實體時出錯: {e}")
                    
                    return entity_data
            
            # 如果直接請求失敗，嘗試在所有吸引設施中查找
            attractions = ThemeParksService.getAttractions()
            for attraction in attractions:
                if attraction.get('id') == str(attraction_id):
                    return attraction
                    
            return None
        except Exception as e:
            print(f"獲取吸引設施時出錯: {e}")
            return None
            
    @staticmethod
    def get_attractions_by_park(park_id):
        """
        從 ThemeParks API 獲取特定公園的所有吸引設施
        
        Args:
            park_id (str): 公園 ID
            
        Returns:
            list: 吸引設施列表
        """
        try:
            response = requests.get(f"{ThemeParksService.BASE_URL}/entity/{park_id}/children")
            
            if response.status_code == 200:
                children = response.json().get('children', [])
                
                # 過濾出類型為 ATTRACTION 的實體
                attractions = []
                park_data = ThemeParksService.getEntityById(park_id)
                
                for attraction in children:
                    if attraction.get('entityType') == 'ATTRACTION':
                        # 添加公園和目的地信息
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
            print(f"獲取公園吸引設施時出錯: {e}")
            return [] 