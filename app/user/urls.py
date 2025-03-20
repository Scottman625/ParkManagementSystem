from django.urls import path
from user import views

app_name = 'user'


urlpatterns = [
    # 用戶身份驗證相關 - 這些端點不需要認證
    path('register/', views.RegisterView.as_view(), name='register'),  # 註冊
    path('login/', views.LoginView.as_view(), name='login'),  # 登入
    path('token/refresh/', views.RefreshTokenView.as_view(), name='token_refresh'),  # 刷新令牌
    
    # 需要認證的端點
    path('logout/', views.LogoutView.as_view(), name='logout'),  # 登出 (需要認證)
    path('token/', views.CreateTokenView.as_view(), name='token'),  # 獲取令牌 (需要認證)
    path('me/', views.ManageUserView.as_view(), name='me'),  # 當前用戶資料 (需要認證)
    path('create/', views.CreateUserView.as_view(), name='create'),  # 管理員創建用戶 (需要管理員權限)
    path('update_password/', views.UpdateUserPassword.as_view(), name='updatepwd'),  # 更新密碼 (需要認證)
    path('update_line_id/', views.UpdateUserLineIdView.as_view(), name='update_line_id'),  # 更新Line ID (需要認證)
    path('update_image/', views.UpdateUserImage.as_view(), name='update_image'),  # 更新用戶頭像 (需要認證)
    path('update_push_notify/', views.GetUpdateUserFCMNotify.as_view(), name='update_push_notify'),  # 更新推送通知設置 (需要認證)
    # UserViewSet中的功能將被通過router註冊，因此下面兩個舊的端點可能會被替代
    # 轉移到UserViewSet.me和UserViewSet.change_password中的功能
]
