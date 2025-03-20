from rest_framework import serializers
from .models import (
    Park, Destination, TicketType, Order, OrderItem, Ticket, CartItem, Cart
)

class DestinationSerializer(serializers.ModelSerializer):
    """Destination serializer"""
    
    class Meta:
        model = Destination
        fields = ['id', 'name', 'slug', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ParkSerializer(serializers.ModelSerializer):
    """Park serializer"""
    destination_name = serializers.CharField(source='destination.name', read_only=True)
    destination_slug = serializers.CharField(source='destination.slug', read_only=True)
    
    class Meta:
        model = Park
        fields = ['id', 'name', 'destination', 'destination_name', 'destination_slug', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at'] 

# Ticket and order related serializers
class TicketTypeSerializer(serializers.ModelSerializer):
    """Ticket type serializer"""
    park_name = serializers.CharField(source='park.name', read_only=True)
    
    class Meta:
        model = TicketType
        fields = ['id', 'name', 'description', 'price', 'park', 'park_name', 'is_active', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class TicketTypeListSerializer(serializers.ModelSerializer):
    """Ticket type list serializer"""
    park_name = serializers.CharField(source='park.name', read_only=True)
    
    class Meta:
        model = TicketType
        fields = ['id', 'name', 'description', 'price', 'park_name', 'is_active']

class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer"""
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'ticket_type', 'ticket_type_name', 'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['id', 'unit_price', 'subtotal']

class OrderItemCreateSerializer(serializers.ModelSerializer):
    """Order item creation serializer"""
    
    class Meta:
        model = OrderItem
        fields = ['ticket_type', 'quantity']
    
    def validate_ticket_type(self, value):
        """Validate that the ticket type is active"""
        if not value.is_active:
            raise serializers.ValidationError("This ticket type is currently not available for purchase")
        return value
    
    def validate_quantity(self, value):
        """Validate that the quantity is reasonable"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero")
        if value > 10:
            raise serializers.ValidationError("Maximum 10 tickets of the same type can be purchased at once")
        return value

class TicketSerializer(serializers.ModelSerializer):
    """Ticket serializer"""
    ticket_type_name = serializers.CharField(source='order_item.ticket_type.name', read_only=True)
    park_name = serializers.CharField(source='order_item.ticket_type.park.name', read_only=True)
    visit_date = serializers.DateField(source='order_item.order.visit_date', read_only=True)
    
    class Meta:
        model = Ticket
        fields = ['id', 'ticket_number', 'ticket_type_name', 'park_name', 'guest_name', 'visit_date', 'is_used', 'used_at', 'qr_code']
        read_only_fields = ['id', 'ticket_number', 'is_used', 'used_at', 'qr_code']

class OrderSerializer(serializers.ModelSerializer):
    """Order serializer"""
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'total_amount', 'status', 'status_display', 'payment_method', 'visit_date', 'notes', 'items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'order_number', 'user', 'total_amount', 'status', 'status_display', 'created_at', 'updated_at']

class OrderCreateSerializer(serializers.ModelSerializer):
    """Order creation serializer"""
    items = OrderItemCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = Order
        fields = ['visit_date', 'notes', 'items']
    
    def validate_visit_date(self, value):
        """Validate that the visit date is not in the past"""
        import datetime
        if value < datetime.date.today():
            raise serializers.ValidationError("Visit date cannot be in the past")
        return value
    
    def validate_items(self, value):
        """Validate that the order has at least one item"""
        if not value:
            raise serializers.ValidationError("Order must contain at least one ticket")
        return value
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        
        # Create order
        order = Order.objects.create(
            user=user,
            total_amount=0,  # Set to 0 initially, will be calculated later
            status=Order.PENDING,
            **validated_data
        )
        
        # Create order items
        for item_data in items_data:
            ticket_type = item_data['ticket_type']
            # Use the current price of the ticket type
            OrderItem.objects.create(
                order=order,
                ticket_type=ticket_type,
                quantity=item_data['quantity'],
                unit_price=ticket_type.price
            )
        
        # Calculate total amount
        order.calculate_total()
        
        # Generate tickets
        self.generate_tickets(order)
        
        return order
    
    def generate_tickets(self, order):
        """Generate tickets for the order"""
        for item in order.items.all():
            for _ in range(item.quantity):
                Ticket.objects.create(order_item=item)

class OrderDetailSerializer(OrderSerializer):
    """Order detail serializer"""
    tickets = serializers.SerializerMethodField()
    
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ['tickets']
    
    def get_tickets(self, obj):
        """Get all tickets under the order"""
        tickets = []
        for item in obj.items.all():
            for ticket in item.tickets.all():
                tickets.append(ticket)
        return TicketSerializer(tickets, many=True).data

class CartItemSerializer(serializers.ModelSerializer):
    ticket_type = TicketTypeSerializer(read_only=True)
    ticket_type_id = serializers.PrimaryKeyRelatedField(
        queryset=TicketType.objects.all(),
        write_only=True,
        source='ticket_type'
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'ticket_type', 'ticket_type_id', 'quantity', 'subtotal', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_subtotal(self, obj):
        return obj.get_subtotal()

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return obj.get_total_price() 