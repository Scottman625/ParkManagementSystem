from django.urls import path
from user import views

app_name = 'user'


urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('create/', views.CreateUserView.as_view(), name='create'),
    path('token/', views.CreateTokenView.as_view(), name='token'),
    path('me/', views.ManageUserView.as_view(), name='me'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('update_password/', views.UpdateUserPassword.as_view(), name='updatepwd'),
    path('update_line_id/', views.UpdateUserLineIdView.as_view(), name='update_line_id'),
    path('update_image/', views.UpdateUserImage.as_view(), name='update_image'),
    path('update_push_notify/', views.GetUpdateUserFCMNotify.as_view(), name='update_push_notify'),
    # UserViewSet中的功能將被通過router註冊，因此下面兩個舊的端點可能會被替代
    # 轉移到UserViewSet.me和UserViewSet.change_password中的功能
]
