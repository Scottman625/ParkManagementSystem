from django.shortcuts import render
from rest_framework import viewsets, status, permissions, mixins
from rest_framework.decorators import action, api_view, permission_classes
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
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.db.models import F, Sum, Case, When, Value, CharField, OuterRef, Subquery
from django.db.models import Count, Avg, Min, Max
from django.db import transaction
import uuid

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
def current_user(request):
    """
    Get information of the currently logged in user
    """
    data = {
        'id': request.user.id,
        'email': request.user.email,
        'name': request.user.name,
        'is_staff': request.user.is_staff,
        'is_authenticated': True,
    }
    return Response(data)

# Ticket and order related viewsets
class TicketTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Ticket type viewset"""
    queryset = TicketType.objects.filter(is_active=True)
    serializer_class = TicketTypeSerializer
    permission_classes = [permissions.AllowAny]
    
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

class OrderViewSet(viewsets.ModelViewSet):
    """Order viewset"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only view their own orders"""
        user = self.request.user
        return Order.objects.filter(user=user).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderSerializer
    
    @action(detail=True, methods=['post'])
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
    
    @action(detail=False, methods=['get'])
    def valid_tickets(self, request):
        """Get user's valid tickets (paid but not used)"""
        tickets = self.get_queryset().filter(
            is_used=False,
            order_item__order__status=Order.PAID
        )
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
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

class CartViewSet(viewsets.GenericViewSet,
                 mixins.RetrieveModelMixin,
                 mixins.DestroyModelMixin):
    """Cart viewset"""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def get_object(self):
        """Get or create user's cart"""
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add item to cart"""
        cart = self.get_object()
        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            ticket_type = serializer.validated_data['ticket_type']
            quantity = serializer.validated_data.get('quantity', 1)
            
            # Check if same ticket type already exists
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                ticket_type=ticket_type,
                defaults={'quantity': quantity}
            )
            
            # If exists, update quantity
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            return Response(CartItemSerializer(cart_item).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_item(self, request, pk=None):
        """Update item quantity in cart"""
        cart = self.get_object()
        try:
            cart_item = cart.items.get(id=request.data.get('item_id'))
        except CartItem.DoesNotExist:
            return Response({'detail': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CartItemSerializer(cart_item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        """Remove item from cart"""
        cart = self.get_object()
        try:
            cart_item = cart.items.get(id=request.data.get('item_id'))
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CartItem.DoesNotExist:
            return Response({'detail': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        """Clear the cart"""
        cart = self.get_object()
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        """Checkout and create order"""
        cart = self.get_object()
        if not cart.items.exists():
            return Response(
                {'detail': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    total_price=cart.get_total_price(),
                    status=Order.PENDING
                )

                # Create order items
                for cart_item in cart.items.all():
                    order_item = OrderItem.objects.create(
                        order=order,
                        ticket_type=cart_item.ticket_type,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.ticket_type.price
                    )
                    
                    # Create tickets for each order item
                    for _ in range(cart_item.quantity):
                        Ticket.objects.create(
                            order_item=order_item,
                            ticket_code=uuid.uuid4()
                        )

                # Clear the cart
                cart.items.all().delete()

                return Response(
                    OrderSerializer(order).data,
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
