from django.shortcuts import render
from rest_framework import viewsets, status, permissions, pagination
from modelCore.models import Destination, Park, Attraction, GuestReview
from .serializers import DestinationSerializer, ParkSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    AttractionSerializer,
    GuestReviewSerializer,
    GuestReviewCreateSerializer,
    AttractionReviewsSerializer
)
from django.db import models

# Create your views here.

def index(request):
    """
    Render the main page
    """
    destinations = Destination.objects.all()
    context = {
        'destinations': destinations,
    }
    return render(request, 'web/index.html', context)

class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for destinations
    
    list:
    Get a list of all destinations
    
    retrieve:
    Get detailed information for a specific destination
    """
    queryset = Destination.objects.all()
    serializer_class = DestinationSerializer

    @swagger_auto_schema(
        operation_description="Get a list of all destinations",
        responses={200: DestinationSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Get detailed information for a specific destination",
        responses={200: DestinationSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

class ParkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for parks
    
    list:
    Get a list of all parks
    
    retrieve:
    Get detailed information for a specific park
    """
    queryset = Park.objects.all()
    serializer_class = ParkSerializer

    @swagger_auto_schema(
        operation_description="Get a list of all parks",
        responses={200: ParkSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    @swagger_auto_schema(
        operation_description="Get all attractions for a specific park",
        responses={200: AttractionSerializer(many=True)}
    )
    def attractions(self, request, *args, **kwargs):
        park = self.get_object()
        attractions = Attraction.objects.filter(park=park)
        serializer = AttractionSerializer(attractions, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Get detailed information for a specific park",
        responses={200: ParkSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

class AttractionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for attractions
    
    list:
    Get a list of all attractions
    
    retrieve:
    Get detailed information for a specific attraction
    """
    queryset = Attraction.objects.all().select_related('park', 'park__destination')
    serializer_class = AttractionSerializer
    pagination_class = pagination.PageNumberPagination

    def get_queryset(self):
        """Optimize queries to reduce database load"""
        # Check if this is for swagger documentation generation
        if getattr(self, 'swagger_fake_view', False):
            return Attraction.objects.none()
            
        queryset = Attraction.objects.all().select_related('park', 'park__destination')
        
        # Filter by query parameters
        park_id = self.request.query_params.get('park')
        if park_id:
            queryset = queryset.filter(park_id=park_id)
            
        destination_id = self.request.query_params.get('destination')
        if destination_id:
            queryset = queryset.filter(park__destination_id=destination_id)
            
        # Return paginated queryset
        return queryset

    @swagger_auto_schema(
        operation_description="Get a list of all attractions",
        responses={200: AttractionSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                'park',
                openapi.IN_QUERY,
                description="Filter by park ID",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=False
            ),
            openapi.Parameter(
                'destination',
                openapi.IN_QUERY,
                description="Filter by destination ID",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get detailed information for a specific attraction",
        responses={200: AttractionSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    @swagger_auto_schema(
        operation_description="Get all reviews for a specific attraction",
        responses={200: AttractionReviewsSerializer()}
    )
    def reviews(self, request, *args, **kwargs):
        """Get all reviews for a specific attraction"""
        # Check if this is for swagger documentation generation
        if getattr(self, 'swagger_fake_view', False):
            return Response({"detail": "Cannot get reviews for swagger fake view"})
            
        attraction = self.get_object()
        serializer = AttractionReviewsSerializer(attraction, context={'request': request})
        return Response(serializer.data)


class GuestReviewViewSet(viewsets.ModelViewSet):
    """
    API endpoints for guest reviews
    
    list:
    Get a list of all reviews
    
    create:
    Create a new review
    
    retrieve:
    Get detailed information for a specific review
    
    update:
    Update a specific review
    
    partial_update:
    Partially update a specific review
    
    destroy:
    Delete a specific review
    
    Note: All APIs require user authentication, which can be achieved through:
    1. Login via the admin page to use Session authentication
    2. Click the Authorize button in the top right corner of Swagger UI for authentication
    """
    queryset = GuestReview.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Choose different serializer based on request type"""
        if self.action == 'create':
            return GuestReviewCreateSerializer
        return GuestReviewSerializer
    
    def get_queryset(self):
        """Get reviews list based on user"""
        # Check if this is a swagger fake view for documentation generation
        if getattr(self, 'swagger_fake_view', False):
            # Return empty queryset to avoid errors during documentation generation
            return GuestReview.objects.none()
            
        user = self.request.user
        # Check if user is authenticated
        if not user.is_authenticated:
            return GuestReview.objects.filter(is_published=True)
            
        if user.is_staff:
            # Admins can see all reviews
            return GuestReview.objects.all()
        # Regular users can only see their own reviews and published reviews
        return GuestReview.objects.filter(
            models.Q(user=user) | models.Q(is_published=True)
        )
    
    def perform_create(self, serializer):
        """Automatically associate review with current user"""
        serializer.save(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Get a list of reviews",
        responses={200: GuestReviewSerializer(many=True)},
        security=[{'Basic': []}, {'Session': []}]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new review",
        request_body=GuestReviewCreateSerializer,
        responses={201: GuestReviewSerializer()},
        security=[{'Basic': []}, {'Session': []}]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get detailed information for a specific review",
        responses={200: GuestReviewSerializer()},
        security=[{'Basic': []}, {'Session': []}]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a specific review",
        request_body=GuestReviewCreateSerializer,
        responses={200: GuestReviewSerializer()},
        security=[{'Basic': []}, {'Session': []}]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update a specific review",
        request_body=GuestReviewCreateSerializer,
        responses={200: GuestReviewSerializer()},
        security=[{'Basic': []}, {'Session': []}]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a specific review",
        responses={204: "No Content"},
        security=[{'Basic': []}, {'Session': []}]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    @swagger_auto_schema(
        operation_description="Get all reviews for the current user",
        responses={200: GuestReviewSerializer(many=True)},
        security=[{'Basic': []}, {'Session': []}]
    )
    def my_reviews(self, request):
        """Get all reviews for the currently logged in user"""
        if not request.user.is_authenticated:
            return Response(
                {"error": "You must be logged in to view your reviews"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        reviews = GuestReview.objects.filter(user=request.user)
        serializer = GuestReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @swagger_auto_schema(
        operation_description="Get all reviews for a specific attraction",
        manual_parameters=[
            openapi.Parameter(
                'attraction_id',
                openapi.IN_QUERY,
                description="Attraction ID",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True
            )
        ],
        responses={200: GuestReviewSerializer(many=True)}
    )
    def attraction_reviews(self, request):
        """Get all reviews for a specific attraction"""
        attraction_id = request.query_params.get('attraction_id')
        if not attraction_id:
            return Response(
                {"error": "Attraction ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attraction = Attraction.objects.get(id=attraction_id)
        except Attraction.DoesNotExist:
            return Response(
                {"error": "Attraction not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        reviews = GuestReview.objects.filter(
            attraction=attraction,
            is_published=True
        )
        serializer = GuestReviewSerializer(reviews, many=True)
        return Response(serializer.data)

