from django.http import JsonResponse
from django.conf import settings
from rest_framework.authtoken.models import Token

class TokenAuthMiddleware:
    """
    自定義中間件，用於在整個應用中強制要求認證
    除了登入、註冊和其他明確允許的路徑外，會驗證所有請求的令牌
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        處理請求，判斷是否需要認證
        """
        # 不需要驗證的路徑
        allowed_paths = [
            '/admin/',
            '/swagger/',
            '/redoc/',
            '/api-auth/',
            '/swagger.json',
            '/swagger.yaml',
            '/static/',
            '/api/user/login/',
            '/api/user/register/',
            '/api/user/token/refresh/',
            '/api/auth/token/',
        ]
        
        # 靜態文件和其他公開資源不需要驗證
        for path in allowed_paths:
            if request.path.startswith(path):
                return self.get_response(request)
        
        # 允許預檢請求（OPTIONS）通過，這是CORS所需的
        if request.method == 'OPTIONS':
            return self.get_response(request)
        
        # 獲取授權頭
        auth_header = request.headers.get('Authorization')
        
        # 檢查是否已經登入 Session
        if request.user and request.user.is_authenticated:
            return self.get_response(request)
        
        # 沒有提供認證頭但請求是列表或詳情操作（允許公開訪問這些API）
        if not auth_header and (request.method == 'GET'):
            # 只允許訪問這些公開路徑的GET請求
            public_api_paths = [
                '/api/destinations/',
                '/api/parks/',
                '/api/attractions/',
                '/api/ticket-types/',
            ]
            
            for path in public_api_paths:
                if request.path.startswith(path):
                    return self.get_response(request)
        
        # 沒有提供認證頭，其他情況需要認證
        if not auth_header:
            return JsonResponse({
                'detail': '認證憑證未提供',
                'code': 'authentication_required'
            }, status=401)
        
        # 檢查令牌格式
        try:
            token_type, token_key = auth_header.split(' ')
            if token_type.lower() != 'token':
                return JsonResponse({
                    'detail': '無效的認證格式，應為: Token <token_key>',
                    'code': 'invalid_token_format'
                }, status=401)
            
            # 驗證令牌
            try:
                token = Token.objects.get(key=token_key)
                # 將用戶附加到請求
                request.user = token.user
                return self.get_response(request)
            except Token.DoesNotExist:
                return JsonResponse({
                    'detail': '提供的認證令牌無效',
                    'code': 'invalid_token'
                }, status=401)
        
        except ValueError:
            return JsonResponse({
                'detail': '無效的認證頭格式',
                'code': 'invalid_header_format'
            }, status=401) 