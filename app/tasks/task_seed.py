import openapi_client
from pprint import pprint
from openapi_client.api import destinations_api
from openapi_client.model.destinations_response import DestinationsResponse
import uuid
from modelCore.models import Destination, Park
from django.db import transaction

def sync_theme_parks():
    """
    使用 ThemeParks API 客戶端獲取數據並同步到數據庫
    """
    # 設定 API 伺服器位址
    configuration = openapi_client.Configuration(
        host="https://api.themeparks.wiki/v1"
    )

    # 創建 API 客戶端
    with openapi_client.ApiClient(configuration) as api_client:
        api_instance = destinations_api.DestinationsApi(api_client)
        
        try:
            # 取得所有支援的樂園清單
            api_response = api_instance.get_destinations()
            
            # 使用資料庫交易確保數據一致性
            with transaction.atomic():
                # 遍歷所有目的地
                for dest_data in api_response.destinations:
                    # 創建或更新目的地
                    destination, created = Destination.objects.update_or_create(
                        id=uuid.UUID(dest_data.id),
                        defaults={
                            'name': dest_data.name,
                            'slug': dest_data.slug
                        }
                    )
                    
                    print(f"{'創建' if created else '更新'} 目的地: {destination.name}")

                    # 處理該目的地的所有公園
                    for park_data in dest_data.parks:
                        park, created = Park.objects.update_or_create(
                            id=uuid.UUID(park_data.id),
                            defaults={
                                'name': park_data.name,
                                'destination': destination
                            }
                        )
                        print(f"{'創建' if created else '更新'} 公園: {park.name}")

            print("數據同步完成！")
            return True, "數據同步成功"

        except openapi_client.ApiException as e:
            error_msg = f"API 調用異常: {str(e)}"
            print(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"同步過程中發生錯誤: {str(e)}"
            print(error_msg)
            return False, error_msg

if __name__ == "__main__":
    sync_theme_parks()