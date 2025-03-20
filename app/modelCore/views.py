from django.shortcuts import render
from rest_framework import viewsets, status, permissions, mixins
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from .models import Park, Destination, TicketType, Order, OrderItem, Ticket, Cart, CartItem
from .database import SyncParkDatabase, ParkDatabase
from .serializers import (
    ParkSerializer, DestinationSerializer, TicketTypeSerializer,
    TicketTypeListSerializer, OrderSerializer, OrderDetailSerializer,
    OrderCreateSerializer, TicketSerializer, CartSerializer, CartItemSerializer
)
from django.conf import settings
from .services import ThemeParksService
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.db.models import F, Sum, Case, When, Value, CharField, OuterRef, Subquery
from django.db.models import Count, Avg, Min, Max
from django.db import transaction
import uuid
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Create API configuration
API_CONFIG = {
    'api_base_url': ThemeParksService.BASE_URL,
    'api_key': getattr(settings, 'PARK_API_KEY', ''),
    'cacheVersion': 1,  # Cache version, can be modified when data structure changes
    'useragent': 'VenueManagementSystem/1.0',
}

# Create singleton instance of SyncParkDatabase
park_db = SyncParkDatabase.get(API_CONFIG)

# Create your views here.

class ParkViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for park information"""
    queryset = Park.objects.all()
    serializer_class = ParkSerializer
    
    def get_queryset(self):
        """Get park queryset, filtered by request parameters"""
        # This method might not be called if we use an external API as data source
        # But we keep it for compatibility
        queryset = super().get_queryset()
        destination_id = self.request.query_params.get('destination_id')
        
        if destination_id:
            queryset = queryset.filter(destination_id=destination_id)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Get list of all parks"""
        try:
            # Use SyncParkDatabase to get all parks
            filter_obj = {}
            if 'destination_id' in request.query_params:
                filter_obj['destination.id'] = request.query_params.get('destination_id')
            
            parks = park_db.getEntities(filter_obj)
            
            serializer = self.get_serializer(parks, many=True)
            return Response(serializer.data)
        except Exception as e:
            # Fall back to database query if API request fails
            return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Get details of a specific park"""
        try:
            # Use SyncParkDatabase to get specific park
            park_id = kwargs['pk']
            park = park_db.getEntityById(park_id)
            
            if park:
                serializer = self.get_serializer(park)
                return Response(serializer.data)
            
            return Response({"error": "Park not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Fall back to database query if API request fails
            return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def by_destination(self, request):
        """Get parks grouped by destination"""
        destination_id = request.query_params.get('destination_id')
        if destination_id:
            try:
                # Use SyncParkDatabase to get parks for specific destination
                parks = park_db.getEntities({'destination.id': destination_id})
                
                serializer = self.get_serializer(parks, many=True)
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": f"Failed to get park data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # If no destination ID specified, return all parks grouped by destination
        try:
            # Use ThemeParksService to get all destinations
            destinations_data = ThemeParksService.get_all_destinations()
            
            result = {}
            for dest_data in destinations_data:
                dest_id = dest_data.get('id')
                
                # Use SyncParkDatabase to get parks for specific destination
                parks = park_db.getEntities({'destination.id': dest_id})
                
                result[dest_id] = self.get_serializer(parks, many=True).data
            
            return Response(result)
        except Exception as e:
            return Response({"error": f"Failed to get park data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for destination information"""
    queryset = Destination.objects.all()
    serializer_class = DestinationSerializer
    
    def list(self, request, *args, **kwargs):
        """Get list of all destinations"""
        try:
            # Use ThemeParksService to get all destination data
            destinations_data = ThemeParksService.get_all_destinations()
            
            # Convert data to destination objects
            destinations = []
            for dest_data in destinations_data:
                destination = Destination(
                    id=dest_data.get('id'),
                    name=dest_data.get('name'),
                    slug=dest_data.get('slug')
                )
                destinations.append(destination)
            
            serializer = self.get_serializer(destinations, many=True)
            return Response(serializer.data)
        except Exception as e:
            # Fall back to database query if API request fails
            return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Get details of a specific destination"""
        try:
            # Use ThemeParksService to get specific destination data
            destination_id = kwargs['pk']
            dest_data = ThemeParksService.get_destination_by_id(destination_id)
            
            if dest_data:
                destination = Destination(
                    id=dest_data.get('id'),
                    name=dest_data.get('name'),
                    slug=dest_data.get('slug')
                )
                serializer = self.get_serializer(destination)
                return Response(serializer.data)
            
            return Response({"error": "Destination not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Fall back to database query if API request fails
            return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def parks(self, request, pk=None):
        """Get all parks for a specific destination"""
        try:
            # Use SyncParkDatabase to get parks for specific destination
            parks = park_db.getEntities({'destination.id': pk})
            
            serializer = ParkSerializer(parks, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": f"Failed to get park data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def current_user(request):
    """
    Get information of the current logged in user
    """
    user = request.user
    return Response({
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'is_staff': user.is_staff
    })

# Ticket and order related viewsets
class TicketTypeViewSet(viewsets.ModelViewSet):
    """Ticket Type Viewset"""
    queryset = TicketType.objects.all()
    serializer_class = TicketTypeSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_permissions(self):
        """
        Set permissions based on action type:
        - List and retrieve views: Allow unauthenticated access
        - Create, update, delete views: Require admin permissions
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TicketTypeListSerializer
        return TicketTypeSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by park
        park_id = self.request.query_params.get('park')
        if park_id:
            queryset = queryset.filter(park_id=park_id)
            
        # Filter by destination
        destination_id = self.request.query_params.get('destination')
        if destination_id:
            queryset = queryset.filter(park__destination_id=destination_id)
            
        return queryset
    
    @swagger_auto_schema(
        operation_description="Get all ticket types",
        responses={200: TicketTypeListSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                'park',
                openapi.IN_QUERY,
                description="Filter by park ID",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'destination',
                openapi.IN_QUERY,
                description="Filter by destination ID",
                type=openapi.TYPE_STRING,
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get details of a specific ticket type",
        responses={200: TicketTypeSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new ticket type (admin only)",
        request_body=TicketTypeSerializer,
        responses={201: TicketTypeSerializer()},
        security=[{'Token': []}]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a ticket type (admin only)",
        request_body=TicketTypeSerializer,
        responses={200: TicketTypeSerializer()},
        security=[{'Token': []}]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a ticket type (admin only)",
        responses={204: "No Content"},
        security=[{'Token': []}]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class OrderViewSet(viewsets.ModelViewSet):
    """Order Viewset"""
    serializer_class = OrderSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Regular users can only view their own orders, admins can view all orders"""
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderSerializer
    
    @swagger_auto_schema(
        operation_description="Get order list (users can only see their own orders)",
        responses={200: OrderSerializer(many=True)},
        security=[{'Token': []}]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get order details",
        responses={200: OrderDetailSerializer()},
        security=[{'Token': []}]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create new order",
        request_body=OrderCreateSerializer,
        responses={201: OrderDetailSerializer()},
        security=[{'Token': []}]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    @swagger_auto_schema(
        operation_description="Cancel an order",
        responses={200: OrderSerializer()},
        security=[{'Token': []}]
    )
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        # Only pending orders can be cancelled
        if order.status != Order.PENDING:
            return Response(
                {'detail': 'Only pending orders can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = Order.CANCELLED
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    @swagger_auto_schema(
        operation_description="Pay for an order",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['payment_method'],
            properties={
                'payment_method': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Payment method, e.g. 'Credit Card', 'PayPal'"
                )
            }
        ),
        responses={200: OrderSerializer()},
        security=[{'Token': []}]
    )
    def pay(self, request, pk=None):
        """Pay for an order (simulation)"""
        order = self.get_object()
        # Only pending orders can be paid
        if order.status != Order.PENDING:
            return Response(
                {'detail': 'Only pending orders can be paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Simulate successful payment
        payment_method = request.data.get('payment_method', 'Credit Card')
        
        order.status = Order.PAID
        order.payment_method = payment_method
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)

class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    """Ticket viewset"""
    serializer_class = TicketSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only view their own tickets"""
        user = self.request.user
        return Ticket.objects.filter(
            order_item__order__user=user
        ).select_related(
            'order_item__ticket_type',
            'order_item__order'
        ).order_by('-order_item__order__created_at')
    
    @swagger_auto_schema(
        operation_description="Get all user tickets",
        responses={200: TicketSerializer(many=True)},
        security=[{'Token': []}]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get ticket details",
        responses={200: TicketSerializer()},
        security=[{'Token': []}]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    @swagger_auto_schema(
        operation_description="Get user's valid tickets (paid but not used)",
        responses={200: TicketSerializer(many=True)},
        security=[{'Token': []}]
    )
    def valid_tickets(self, request):
        """Get user's valid tickets (paid but not used)"""
        tickets = self.get_queryset().filter(
            is_used=False,
            order_item__order__status=Order.PAID
        )
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    @swagger_auto_schema(
        operation_description="Update ticket guest name",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['guest_name'],
            properties={
                'guest_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Guest name"
                )
            }
        ),
        responses={200: TicketSerializer()},
        security=[{'Token': []}]
    )
    def update_guest(self, request, pk=None):
        """Update the guest name on a ticket"""
        ticket = self.get_object()
        
        # Only paid and unused tickets can have guest name updated
        if ticket.order_item.order.status != Order.PAID or ticket.is_used:
            return Response(
                {'detail': 'Only paid and unused tickets can have guest name updated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guest_name = request.data.get('guest_name')
        if not guest_name:
            return Response(
                {'detail': 'Guest name must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ticket.guest_name = guest_name
        ticket.save()
        
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)

class CartViewSet(viewsets.ModelViewSet):
    """Shopping Cart Viewset"""
    serializer_class = CartSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Users can only view their own carts"""
        user = self.request.user
        return Cart.objects.filter(user=user)
    
    def perform_create(self, serializer):
        """Ensure cart is associated with the current user"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add item to cart"""
        cart = self.get_object()
        
        try:
            ticket_type_id = request.data.get('ticket_type')
            if not ticket_type_id:
                return Response({"detail": "Ticket type ID is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            ticket_type = TicketType.objects.get(id=ticket_type_id)
            quantity = int(request.data.get('quantity', 1))
            
            # Check if item already exists in cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                ticket_type=ticket_type,
                defaults={'quantity': quantity}
            )
            
            # If item exists, increase quantity
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
                
            return Response(CartSerializer(cart).data)
            
        except TicketType.DoesNotExist:
            return Response({"detail": "Specified ticket type does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        """Remove item from cart"""
        cart = self.get_object()
        
        try:
            item_id = request.data.get('item_id')
            if not item_id:
                return Response({"detail": "Cart item ID is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            item = CartItem.objects.get(id=item_id, cart=cart)
            item.delete()
                
            return Response(CartSerializer(cart).data)
            
        except CartItem.DoesNotExist:
            return Response({"detail": "Specified cart item does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_quantity(self, request, pk=None):
        """Update cart item quantity"""
        cart = self.get_object()
        
        try:
            item_id = request.data.get('item_id')
            quantity = int(request.data.get('quantity', 1))
            
            if not item_id:
                return Response({"detail": "Cart item ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            if quantity < 1:
                return Response({"detail": "Quantity must be greater than 0"}, status=status.HTTP_400_BAD_REQUEST)
                
            item = CartItem.objects.get(id=item_id, cart=cart)
            item.quantity = quantity
            item.save()
                
            return Response(CartSerializer(cart).data)
            
        except CartItem.DoesNotExist:
            return Response({"detail": "Specified cart item does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        """Clear the cart"""
        cart = self.get_object()
        cart.items.all().delete()
        return Response(CartSerializer(cart).data)
