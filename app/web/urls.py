from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'web'

# 在主URLs中已定義API路由
# router = DefaultRouter()
# router.register(r'destinations', views.DestinationViewSet)
# router.register(r'parks', views.ParkViewSet)
# router.register(r'attractions', views.AttractionViewSet)

urlpatterns = [
    path('', views.index, name='index'),
    # API路徑已移至主URLs配置中
    # path('api/', include(router.urls)),
]