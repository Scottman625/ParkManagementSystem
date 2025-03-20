import openapi_client
from pprint import pprint
from openapi_client.api import destinations_api
from openapi_client.model.destinations_response import DestinationsResponse

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
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling DestinationsApi->get_destinations: %s\n" % e)
