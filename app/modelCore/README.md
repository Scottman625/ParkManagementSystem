# 主題公園數據同步

本模塊提供了與 ThemeParks API 同步數據的功能，包括目的地、公園和吸引設施信息。

## 模型結構

- `Destination`: 代表一個目的地（如東京迪士尼度假區）
- `Park`: 代表一個公園（如東京迪士尼樂園）
- `Attraction`: 代表一個吸引設施（如加勒比海盜）

## 管理命令

### sync_entities

這是推薦使用的命令，用於從 ThemeParks API 同步實體到數據庫。

用法：

```bash
# 同步所有實體
python manage.py sync_entities

# 強制同步所有實體（忽略緩存）
python manage.py sync_entities --force

# 只同步特定類型的實體
python manage.py sync_entities --entity-type destination
python manage.py sync_entities --entity-type park
python manage.py sync_entities --entity-type attraction

# 只同步特定 ID 的實體
python manage.py sync_entities --entity-type destination --entity-id [destination_id]
python manage.py sync_entities --entity-type park --entity-id [park_id]
python manage.py sync_entities --entity-type attraction --entity-id [attraction_id]
```

### sync_themeparks

這是舊版命令，內部調用 `sync_entities` 命令。為了向後兼容而保留。

用法：

```bash
python manage.py sync_themeparks
```

## 服務類

### ThemeParksService

提供與 ThemeParks API 交互的方法。

主要方法：

- `get_all_destinations()`: 獲取所有目的地
- `getDestinationById(destination_id)`: 獲取特定目的地
- `getEntities()`: 獲取所有公園
- `getEntityById(entity_id)`: 獲取特定公園
- `findEntities(filter_obj)`: 根據條件查找公園
- `getAttractions()`: 獲取所有吸引設施
- `getAttractionById(attraction_id)`: 獲取特定吸引設施
- `get_attractions_by_park(park_id)`: 獲取特定公園的所有吸引設施

## 模型方法

每個模型都實現了 `create_from_entity` 方法，用於從 API 返回的數據創建或更新數據庫記錄：

```python
# 創建或更新目的地
destination = Destination.create_from_entity(destination_data)

# 創建或更新公園
park = Park.create_from_entity(park_data)

# 創建或更新吸引設施
attraction = Attraction.create_from_entity(attraction_data)
```

## API 端點

本模塊提供了以下 API 端點：

- `/api/parks/`: 獲取所有公園
- `/api/parks/<id>/`: 獲取特定公園
- `/api/destinations/`: 獲取所有目的地
- `/api/destinations/<id>/`: 獲取特定目的地
- `/api/destinations/<id>/parks/`: 獲取特定目的地的所有公園
- `/api/attractions/`: 獲取所有吸引設施
- `/api/attractions/<id>/`: 獲取特定吸引設施
- `/api/parks/<id>/attractions/`: 獲取特定公園的所有吸引設施

## 示例代碼

```python
from modelCore.services import ThemeParksService
from modelCore.models import Destination, Park, Attraction

# 獲取所有目的地
destinations = ThemeParksService.get_all_destinations()

# 獲取特定目的地
destination = ThemeParksService.getDestinationById('destination_id')

# 獲取所有公園
parks = ThemeParksService.getEntities()

# 獲取特定公園
park = ThemeParksService.getEntityById('park_id')

# 獲取特定目的地的所有公園
parks = ThemeParksService.findEntities({'destination.id': 'destination_id'})

# 獲取所有吸引設施
attractions = ThemeParksService.getAttractions()

# 獲取特定吸引設施
attraction = ThemeParksService.getAttractionById('attraction_id')

# 獲取特定公園的所有吸引設施
attractions = ThemeParksService.get_attractions_by_park('park_id')

# 創建或更新目的地
destination_obj = Destination.create_from_entity(destination)

# 創建或更新公園
park_obj = Park.create_from_entity(park)

# 創建或更新吸引設施
attraction_obj = Attraction.create_from_entity(attraction)
```

## 實體關係

```
Destination (目的地)
    ↑
    └── Park (公園)
           ↑
           └── Attraction (吸引設施)
```

每個吸引設施必須位於一個公園內，每個公園必須屬於一個目的地。 