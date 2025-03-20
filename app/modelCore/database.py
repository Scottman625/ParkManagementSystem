import asyncio
import aiohttp
import json
import requests
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from .models import Park, Destination
from .services import ThemeParksService

class Cache:
    """簡單的緩存類，用於緩存資料"""
    
    def __init__(self, name, version=0):
        """
        初始化緩存
        
        Args:
            name (str): 緩存名稱
            version (int): 緩存版本
        """
        self.name = name
        self.version = version
        self._cache = {}
        self._cache_times = {}
    
    def wrap(self, key, callback, ttl=60000):
        """
        包裝一個回調函數，如果緩存中有數據則返回緩存，否則執行回調並緩存結果
        
        Args:
            key (str): 緩存鍵
            callback (callable): 獲取數據的回調函數
            ttl (int): 緩存時間（毫秒）
            
        Returns:
            object: 緩存數據或回調結果
        """
        full_key = f"{self.name}_{self.version}_{key}"
        
        # 檢查緩存是否存在且未過期
        now = time.time() * 1000  # 轉換為毫秒
        if full_key in self._cache and (now - self._cache_times.get(full_key, 0)) < ttl:
            return self._cache[full_key]
        
        # 執行回調並緩存結果
        result = callback()
        self._cache[full_key] = result
        self._cache_times[full_key] = now
        
        return result
    
    def clear(self, key=None):
        """
        清除緩存
        
        Args:
            key (str, optional): 要清除的特定鍵，如果為 None 則清除所有緩存
        """
        if key is None:
            self._cache = {}
            self._cache_times = {}
        else:
            full_key = f"{self.name}_{self.version}_{key}"
            if full_key in self._cache:
                del self._cache[full_key]
                del self._cache_times[full_key]

class HTTP:
    """簡單的 HTTP 客戶端，用於發送 API 請求"""
    
    def __init__(self):
        """初始化 HTTP 客戶端"""
        self.useragent = "ThemeParkAPI/1.0"
        self._injectors = []
    
    def injectForDomain(self, filter_obj, callback):
        """
        為特定域名注入回調函數
        
        Args:
            filter_obj (dict): 過濾條件
            callback (callable): 注入的回調函數
        """
        self._injectors.append((filter_obj, callback))
    
    def get(self, url, params=None, headers=None):
        """
        發送 GET 請求
        
        Args:
            url (str): 請求 URL
            params (dict, optional): 查詢參數
            headers (dict, optional): 請求頭
            
        Returns:
            requests.Response: 響應對象
        """
        if headers is None:
            headers = {}
        
        if 'User-Agent' not in headers and self.useragent:
            headers['User-Agent'] = self.useragent
        
        # 執行注入的回調
        for filter_obj, callback in self._injectors:
            if 'hostname' in filter_obj and filter_obj['hostname'].get('$exists', False):
                callback('GET', url)
        
        return requests.get(url, params=params, headers=headers)

# 數據庫單例存儲
Databases = {}

class Database:
    """處理景點/公園數據的獲取和存儲的類"""

    def __init__(self, options=None):
        """
        構造一個新的 Database 對象
        
        Args:
            options (dict, optional): 配置選項
        """
        self.config = options or {}
        self.config['useragent'] = self.config.get('useragent', None)
        
        self.cache = Cache(self.__class__.__name__, self.config.get('cacheVersion', 0))
        self.http = HTTP()
        
        if self.config.get('useragent'):
            self.http.useragent = self.config['useragent']
        
        self.http.injectForDomain({'hostname': {'$exists': True}}, lambda method, url: self.log(method, url))
        
        self.initialized = False
        self.entities = []
        self.api_base_url = self.config.get('api_base_url', ThemeParksService.BASE_URL)
        self.api_key = self.config.get('api_key', '')
    
    def log(self, *args):
        """
        打印日誌
        
        Args:
            *args: 要打印的參數
        """
        class_name = self.__class__.__name__
        print(f"[{class_name}]", *args)
    
    @classmethod
    def get(cls, options=None):
        """
        獲取此類的單例
        
        Args:
            options (dict, optional): 要傳遞給新實例的選項。
                                     只有在實例尚不存在時才會使用
                                     
        Returns:
            Database: 數據庫實例
        """
        class_name = cls.__name__
        if class_name not in Databases:
            Databases[class_name] = cls(options)
        return Databases[class_name]
    
    async def init(self):
        """初始化數據庫連接並獲取數據"""
        if not self.initialized:
            await self._init()
            self.entities = await self._getEntities()
            self.initialized = True
        return self
    
    @abstractmethod
    async def _init(self):
        """
        內部初始化函數，在子類中重寫以實現具體功能
        """
        pass
    
    @abstractmethod
    async def _getEntities(self):
        """
        返回此景點/公園的所有實體
        
        Returns:
            list: 實體對象列表
        """
        pass
    
    async def findEntity(self, filter_opt=None):
        """
        從數據庫中查找單個實體
        
        Args:
            filter_opt (dict, optional): 過濾選項
            
        Returns:
            object: 符合過濾條件的實體
        """
        if not self.initialized:
            await self.init()
        
        if not filter_opt:
            return self.entities[0] if self.entities else None
        
        for entity in self.entities:
            match = True
            for key, value in filter_opt.items():
                if not hasattr(entity, key) or getattr(entity, key) != value:
                    match = False
                    break
            if match:
                return entity
        
        return None
    
    async def fetch_api_data(self, endpoint, params=None):
        """
        從 API 獲取數據
        
        Args:
            endpoint (str): API 端點
            params (dict, optional): 查詢參數
            
        Returns:
            dict: API 響應數據
        """
        url = f"{self.api_base_url}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"API 請求失敗: {response.status} {await response.text()}")

class ParkDatabase(Database):
    """處理公園數據的具體實現"""
    
    async def _init(self):
        """初始化公園數據庫連接"""
        # 可以在這裡進行 API 認證等操作
        pass
    
    async def _getEntities(self):
        """獲取所有公園數據"""
        try:
            # 通過 API 獲取公園數據
            data = await self.fetch_api_data('destinations')
            
            # 解析 API 響應數據，轉換為公園對象
            parks = []
            for dest_data in data.get('destinations', []):
                for park_data in dest_data.get('parks', []):
                    park = self._parse_park_data(park_data, dest_data)
                    if park:
                        parks.append(park)
            
            return parks
        except Exception as e:
            print(f"獲取公園數據時出錯: {e}")
            return []
    
    def _parse_park_data(self, park_data, destination_data=None):
        """
        解析 API 返回的公園數據
        
        Args:
            park_data (dict): API 返回的公園數據
            destination_data (dict, optional): API 返回的目的地數據
            
        Returns:
            Park: 公園對象
        """
        try:
            # 創建一個公園對象，但不保存到數據庫
            park = Park(
                id=park_data.get('id'),
                name=park_data.get('name'),
            )
            
            # 如果有目的地數據，設置目的地屬性
            if destination_data:
                destination = Destination(
                    id=destination_data.get('id'),
                    name=destination_data.get('name'),
                    slug=destination_data.get('slug')
                )
                park.destination = destination
            
            return park
        except Exception as e:
            print(f"解析公園數據時出錯: {e}")
            return None
    
    async def get_park_by_id(self, park_id):
        """
        根據 ID 獲取公園
        
        Args:
            park_id (uuid): 公園 ID
            
        Returns:
            Park: 公園對象
        """
        try:
            # 首先嘗試從本地緩存中查找
            park = await self.findEntity({'id': park_id})
            if park:
                return park
            
            # 如果本地沒有，則通過 API 獲取目的地數據
            destinations_data = await self.fetch_api_data('destinations')
            
            # 遍歷所有目的地和公園，查找匹配的公園 ID
            for dest_data in destinations_data.get('destinations', []):
                for park_data in dest_data.get('parks', []):
                    if park_data.get('id') == str(park_id):
                        return self._parse_park_data(park_data, dest_data)
            
            return None
        except Exception as e:
            print(f"獲取公園時出錯: {e}")
            return None
    
    async def get_parks_by_destination(self, destination_id):
        """
        根據目的地 ID 獲取公園列表
        
        Args:
            destination_id (uuid): 目的地 ID
            
        Returns:
            list: 公園對象列表
        """
        try:
            # 通過 API 獲取目的地數據
            destinations_data = await self.fetch_api_data('destinations')
            
            # 查找匹配的目的地
            parks = []
            for dest_data in destinations_data.get('destinations', []):
                if dest_data.get('id') == str(destination_id):
                    # 找到匹配的目的地，處理其所有公園
                    for park_data in dest_data.get('parks', []):
                        park = self._parse_park_data(park_data, dest_data)
                        if park:
                            parks.append(park)
                    break
            
            return parks
        except Exception as e:
            print(f"獲取目的地公園時出錯: {e}")
            
            # 如果 API 失敗，則嘗試從本地緩存中過濾
            parks = []
            for entity in self.entities:
                if hasattr(entity, 'destination') and entity.destination and str(entity.destination.id) == str(destination_id):
                    parks.append(entity)
            return parks

# 同步版本的公園數據庫
class SyncParkDatabase:
    """同步版本的公園數據庫，不使用異步"""
    
    _instances = {}
    
    @classmethod
    def get(cls, options=None):
        """
        獲取此類的單例
        
        Args:
            options (dict, optional): 要傳遞給新實例的選項
                                     
        Returns:
            SyncParkDatabase: 數據庫實例
        """
        if cls not in cls._instances:
            cls._instances[cls] = cls(options)
        return cls._instances[cls]
    
    def __init__(self, options=None):
        """
        構造一個新的 SyncParkDatabase 對象
        
        Args:
            options (dict, optional): 配置選項
        """
        self.config = options or {}
        self.useragent = self.config.get('useragent', "ThemeParkAPI/1.0")
        
        self.cache = Cache(self.__class__.__name__, self.config.get('cacheVersion', 0))
        self.http = HTTP()
        
        if self.useragent:
            self.http.useragent = self.useragent
        
        self.http.injectForDomain({'hostname': {'$exists': True}}, lambda method, url: self.log(method, url))
        
        self.api_base_url = self.config.get('api_base_url', ThemeParksService.BASE_URL)
        self.api_key = self.config.get('api_key', '')
    
    def log(self, *args):
        """
        打印日誌
        
        Args:
            *args: 要打印的參數
        """
        class_name = self.__class__.__name__
        print(f"[{class_name}]", *args)
    
    def _parse_park_data(self, park_data):
        """
        解析 API 返回的公園數據
        
        Args:
            park_data (dict): API 返回的公園數據
            
        Returns:
            Park: 公園對象
        """
        try:
            # 創建一個公園對象，但不保存到數據庫
            park = Park(
                id=park_data.get('id'),
                name=park_data.get('name'),
            )
            
            # 如果有目的地數據，設置目的地屬性
            if 'destination' in park_data and park_data['destination']:
                destination = Destination(
                    id=park_data['destination'].get('id'),
                    name=park_data['destination'].get('name'),
                    slug=park_data['destination'].get('slug')
                )
                park.destination = destination
            
            return park
        except Exception as e:
            print(f"解析公園數據時出錯: {e}")
            return None
    
    def getEntities(self, filter_obj=None):
        """
        獲取所有公園實體
        
        Args:
            filter_obj (dict, optional): 過濾條件
            
        Returns:
            list: 公園對象列表
        """
        # 使用緩存獲取所有實體
        def get_all_parks_callback():
            return self.get_all_parks()
        
        entities = self.cache.wrap('entities', get_all_parks_callback, 60000)  # 緩存一分鐘
        
        # 如果有過濾條件，則應用過濾
        if filter_obj:
            return [entity for entity in entities if self._match_filter(entity, filter_obj)]
        
        return entities
    
    def _match_filter(self, entity, filter_obj):
        """
        檢查實體是否匹配過濾條件
        
        Args:
            entity: 要檢查的實體
            filter_obj (dict): 過濾條件
            
        Returns:
            bool: 是否匹配
        """
        for key, value in filter_obj.items():
            # 如果實體沒有該屬性，則不匹配
            if not hasattr(entity, key):
                return False
            
            # 獲取實體的屬性值
            entity_value = getattr(entity, key)
            
            # 檢查值是否匹配
            if isinstance(value, dict):
                # 處理特殊操作符
                if '$exists' in value:
                    if value['$exists'] and entity_value is None:
                        return False
                    elif not value['$exists'] and entity_value is not None:
                        return False
                # 其他運算符...
            elif str(entity_value) != str(value):  # 轉換為字符串進行比較
                return False
        
        return True
    
    def findEntity(self, filter_obj=None):
        """
        從數據庫中查找單個實體
        
        Args:
            filter_obj (dict, optional): 過濾選項
            
        Returns:
            Park: 符合過濾條件的公園
        """
        entities = self.getEntities()
        
        if not filter_obj:
            return entities[0] if entities else None
        
        for entity in entities:
            if self._match_filter(entity, filter_obj):
                return entity
        
        return None
    
    def getEntityById(self, entity_id):
        """
        根據 ID 獲取實體對象
        
        Args:
            entity_id (str): 實體 ID
            
        Returns:
            object: 實體對象
        """
        return self.findEntity({'id': str(entity_id)})
    
    def get_all_parks(self):
        """
        獲取所有公園
        
        Returns:
            list: 公園對象列表
        """
        try:
            # 使用 ThemeParksService 獲取所有公園
            parks_data = ThemeParksService.get_all_parks()
            
            # 解析公園數據
            parks = []
            for park_data in parks_data:
                park = self._parse_park_data(park_data)
                if park:
                    parks.append(park)
            
            return parks
        except Exception as e:
            print(f"獲取所有公園時出錯: {e}")
            # 如果 API 失敗，則嘗試從數據庫中獲取
            return Park.objects.all().select_related('destination')
    
    def get_park_by_id(self, park_id):
        """
        根據 ID 獲取公園
        
        Args:
            park_id (uuid): 公園 ID
            
        Returns:
            Park: 公園對象，如果找不到則返回 None
        """
        return self.getEntityById(park_id)
    
    def get_parks_by_destination(self, destination_id):
        """
        根據目的地 ID 獲取公園列表
        
        Args:
            destination_id (uuid): 目的地 ID
            
        Returns:
            list: 公園對象列表
        """
        try:
            # 使用 ThemeParksService 獲取特定目的地的公園
            parks_data = ThemeParksService.get_parks_by_destination(destination_id)
            
            # 解析公園數據
            parks = []
            for park_data in parks_data:
                park = self._parse_park_data(park_data)
                if park:
                    parks.append(park)
            
            return parks
        except Exception as e:
            print(f"獲取目的地公園時出錯: {e}")
            # 如果 API 失敗，則嘗試從數據庫中獲取
            return Park.objects.filter(destination_id=destination_id) 