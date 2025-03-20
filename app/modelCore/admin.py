from django.contrib import admin
from .models import (
    User, Destination, Park, Attraction, GuestReview,
    TicketType, Order, OrderItem, Ticket
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'name', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff']
    search_fields = ['email', 'name']

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['name', 'slug']

@admin.register(Park)
class ParkAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'destination', 'created_at', 'updated_at']
    list_filter = ['destination', 'created_at']
    search_fields = ['name']

@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'park', 'attraction_type', 'entity_type', 'created_at', 'updated_at']
    list_filter = ['park', 'attraction_type', 'entity_type', 'created_at']
    search_fields = ['name', 'description']

@admin.register(GuestReview)
class GuestReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'attraction', 'rating', 'visit_date', 'is_published', 'created_at']
    list_filter = ['rating', 'is_published', 'visit_date', 'created_at']
    search_fields = ['user__name', 'attraction__name', 'content']
    list_editable = ['is_published']

@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'park', 'price', 'is_active', 'created_at']
    list_filter = ['park', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'is_active']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']

class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    readonly_fields = ['ticket_number']
    fields = ['ticket_number', 'guest_name', 'is_used', 'used_at']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'total_amount', 'status', 'visit_date', 'created_at']
    list_filter = ['status', 'visit_date', 'created_at']
    search_fields = ['order_number', 'user__email', 'user__name']
    readonly_fields = ['order_number', 'total_amount']
    inlines = [OrderItemInline]
    actions = ['mark_as_paid', 'mark_as_cancelled']
    
    def mark_as_paid(self, request, queryset):
        queryset.update(status=Order.PAID)
    mark_as_paid.short_description = "標記為已付款"
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status=Order.CANCELLED)
    mark_as_cancelled.short_description = "標記為已取消"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'ticket_type', 'quantity', 'unit_price', 'subtotal']
    list_filter = ['order__status', 'ticket_type']
    search_fields = ['order__order_number', 'ticket_type__name']
    readonly_fields = ['subtotal']
    inlines = [TicketInline]

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'order_item', 'guest_name', 'is_used', 'used_at']
    list_filter = ['is_used', 'order_item__order__visit_date']
    search_fields = ['ticket_number', 'guest_name', 'order_item__order__order_number']
    readonly_fields = ['ticket_number', 'qr_code']
    actions = ['mark_as_used']
    
    def mark_as_used(self, request, queryset):
        for ticket in queryset:
            ticket.mark_as_used()
    mark_as_used.short_description = "標記為已使用"
