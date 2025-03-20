from django.test import TestCase
from django.core.management import call_command
from unittest.mock import patch, MagicMock
from io import StringIO
from modelCore.models import Destination, Park, Attraction
import uuid

class SyncEntitiesCommandTest(TestCase):
    """測試同步實體命令的功能"""

    @patch('modelCore.services.ThemeParksService.get_all_destinations')
    @patch('modelCore.services.ThemeParksService.getEntities')
    @patch('modelCore.services.ThemeParksService.getAttractions')
    def test_sync_all_entities(self, mock_get_attractions, mock_get_entities, mock_get_all_destinations):
        """測試同步所有實體的功能"""
        # 模擬 API 返回的目的地數據
        destination_id1 = str(uuid.uuid4())
        destination_id2 = str(uuid.uuid4())
        
        mock_get_all_destinations.return_value = [
            {
                'id': destination_id1,
                'name': '測試目的地 1',
                'slug': 'test-destination-1'
            },
            {
                'id': destination_id2,
                'name': '測試目的地 2',
                'slug': 'test-destination-2'
            }
        ]

        # 模擬 API 返回的公園數據
        park_id1 = str(uuid.uuid4())
        park_id2 = str(uuid.uuid4())
        
        mock_get_entities.return_value = [
            {
                'id': park_id1,
                'name': '測試公園 1',
                'destination': {
                    'id': destination_id1,
                    'name': mock_get_all_destinations.return_value[0]['name'],
                    'slug': mock_get_all_destinations.return_value[0]['slug']
                }
            },
            {
                'id': park_id2,
                'name': '測試公園 2',
                'destination': {
                    'id': destination_id2,
                    'name': mock_get_all_destinations.return_value[1]['name'],
                    'slug': mock_get_all_destinations.return_value[1]['slug']
                }
            }
        ]
        
        # 模擬 API 返回的吸引設施數據
        mock_get_attractions.return_value = [
            {
                'id': str(uuid.uuid4()),
                'name': '測試吸引設施 1',
                'entityType': 'ATTRACTION',
                'description': '測試吸引設施 1 描述',
                'park': {
                    'id': park_id1,
                    'name': '測試公園 1',
                },
                'destination': {
                    'id': destination_id1,
                    'name': '測試目的地 1',
                    'slug': 'test-destination-1'
                }
            },
            {
                'id': str(uuid.uuid4()),
                'name': '測試吸引設施 2',
                'entityType': 'ATTRACTION',
                'description': '測試吸引設施 2 描述',
                'park': {
                    'id': park_id2,
                    'name': '測試公園 2',
                },
                'destination': {
                    'id': destination_id2,
                    'name': '測試目的地 2',
                    'slug': 'test-destination-2'
                }
            }
        ]

        # 捕獲命令輸出
        out = StringIO()
        call_command('sync_entities', stdout=out)
        output = out.getvalue()

        # 檢查命令是否成功執行
        self.assertIn('成功同步', output)
        self.assertIn('同步完成', output)

        # 檢查數據庫是否有目的地、公園和吸引設施數據
        self.assertEqual(Destination.objects.count(), 2)
        self.assertEqual(Park.objects.count(), 2)
        self.assertEqual(Attraction.objects.count(), 2)

    @patch('modelCore.services.ThemeParksService.getDestinationById')
    def test_sync_specific_destination(self, mock_get_destination_by_id):
        """測試同步特定目的地的功能"""
        dest_id = str(uuid.uuid4())
        
        # 模擬 API 返回的目的地數據
        mock_get_destination_by_id.return_value = {
            'id': dest_id,
            'name': '特定測試目的地',
            'slug': 'specific-test-destination',
            'parks': [
                {
                    'id': str(uuid.uuid4()),
                    'name': '特定測試公園'
                }
            ]
        }

        # 捕獲命令輸出
        out = StringIO()
        call_command('sync_entities', entity_type='destination', entity_id=dest_id, stdout=out)
        output = out.getvalue()

        # 檢查命令是否成功執行
        self.assertIn('目的地 "特定測試目的地" 已同步', output)
        
        # 檢查數據庫是否有特定目的地數據
        self.assertEqual(Destination.objects.filter(id=dest_id).count(), 1)

    @patch('modelCore.services.ThemeParksService.getEntityById')
    def test_sync_specific_park(self, mock_get_entity_by_id):
        """測試同步特定公園的功能"""
        park_id = str(uuid.uuid4())
        dest_id = str(uuid.uuid4())
        
        # 模擬 API 返回的公園數據
        mock_get_entity_by_id.return_value = {
            'id': park_id,
            'name': '特定測試公園',
            'destination': {
                'id': dest_id,
                'name': '特定測試目的地',
                'slug': 'specific-test-destination'
            }
        }

        # 捕獲命令輸出
        out = StringIO()
        call_command('sync_entities', entity_type='park', entity_id=park_id, stdout=out)
        output = out.getvalue()

        # 檢查命令是否成功執行
        self.assertIn('公園 "特定測試公園" 已同步', output)
        
        # 檢查數據庫是否有特定公園數據
        self.assertEqual(Park.objects.filter(id=park_id).count(), 1)
        self.assertEqual(Destination.objects.filter(id=dest_id).count(), 1)
        
    @patch('modelCore.services.ThemeParksService.getAttractionById')
    def test_sync_specific_attraction(self, mock_get_attraction_by_id):
        """測試同步特定吸引設施的功能"""
        attraction_id = str(uuid.uuid4())
        park_id = str(uuid.uuid4())
        dest_id = str(uuid.uuid4())
        
        # 先創建一個目的地和公園，因為吸引設施需要關聯到公園
        destination = Destination.objects.create(
            id=dest_id,
            name='測試目的地',
            slug='test-destination'
        )
        
        park = Park.objects.create(
            id=park_id,
            name='測試公園',
            destination=destination
        )
        
        # 模擬 API 返回的吸引設施數據
        mock_get_attraction_by_id.return_value = {
            'id': attraction_id,
            'name': '特定測試吸引設施',
            'entityType': 'ATTRACTION',
            'description': '特定測試吸引設施描述',
            'park': {
                'id': park_id,
                'name': '測試公園'
            },
            'destination': {
                'id': dest_id,
                'name': '測試目的地',
                'slug': 'test-destination'
            }
        }

        # 捕獲命令輸出
        out = StringIO()
        call_command('sync_entities', entity_type='attraction', entity_id=attraction_id, stdout=out)
        output = out.getvalue()

        # 檢查命令是否成功執行
        self.assertIn('吸引設施 "特定測試吸引設施" 已同步', output)
        
        # 檢查數據庫是否有特定吸引設施數據
        self.assertEqual(Attraction.objects.filter(id=attraction_id).count(), 1)
        attraction = Attraction.objects.get(id=attraction_id)
        self.assertEqual(attraction.name, '特定測試吸引設施')
        self.assertEqual(attraction.park.id, uuid.UUID(park_id)) 