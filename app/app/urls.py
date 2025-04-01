"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from api.views import DestinationViewSet, ParkViewSet, AttractionViewSet, GuestReviewViewSet
from rest_framework.routers import DefaultRouter
from modelCore.views import TicketTypeViewSet, OrderViewSet, TicketViewSet, CartViewSet
from user.views import UserViewSet, CreateTokenView

# Create API router
router = DefaultRouter()
router.register(r'destinations', DestinationViewSet)
router.register(r'parks', ParkViewSet)
router.register(r'attractions', AttractionViewSet)
router.register(r'users', UserViewSet)
router.register(r'reviews', GuestReviewViewSet)
router.register(r'ticket-types', TicketTypeViewSet)
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'cart', CartViewSet, basename='cart')

# Swagger info definition
swagger_info = openapi.Info(
    title="Theme Park Management System API",
    default_version='v1',
    description="API documentation for the Theme Park Management System, including all module endpoints",
    terms_of_service="https://www.google.com/policies/terms/",
    contact=openapi.Contact(email="contact@example.com"),
    license=openapi.License(name="BSD License"),
)

# Swagger documentation setup
schema_view = get_schema_view(
    swagger_info,
    public=True,
    permission_classes=[permissions.AllowAny],
    patterns=[
        path('api/', include(router.urls)),
        path('api/user/', include('user.urls')),
        path('api/modelCore/', include('modelCore.urls')),
    ],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("api.urls")),
    path('api/', include(router.urls)),
    path('api/user/', include('user.urls')),
    path('api/modelCore/', include('modelCore.urls')),
    
    # 令牌認證 - 使用自定義的CreateTokenView替代DRF的obtain_auth_token
    path('api/auth/token/', CreateTokenView.as_view(), name='api_token_auth'),
    
    # Swagger URLs
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api-auth/', include('rest_framework.urls')),
]
