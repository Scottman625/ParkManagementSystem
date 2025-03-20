from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'modelCore'

router = DefaultRouter()
router.register(r'parks', views.ParkViewSet)
router.register(r'destinations', views.DestinationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('current-user/', views.current_user, name='current-user'),
] 