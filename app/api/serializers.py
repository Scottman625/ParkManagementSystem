from rest_framework import serializers
from modelCore.models import Destination, Park, Attraction, GuestReview, User

class ParkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Park
        fields = ['id', 'name', 'created_at', 'updated_at']
        ref_name = 'WebParkSerializer'

class DestinationSerializer(serializers.ModelSerializer):
    parks = ParkSerializer(many=True, read_only=True)

    class Meta:
        model = Destination
        fields = ['id', 'name', 'slug', 'parks', 'created_at', 'updated_at'] 
        ref_name = 'WebDestinationSerializer'

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'image']
        ref_name = 'WebUserSimpleSerializer'

class GuestReviewSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = GuestReview
        fields = ['id', 'attraction', 'user', 'rating', 'content', 'visit_date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        ref_name = 'WebGuestReviewSerializer'

class GuestReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestReview
        fields = ['attraction', 'rating', 'content', 'visit_date']
        ref_name = 'WebGuestReviewCreateSerializer'
        
    def create(self, validated_data):
        # Get current user from request context
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("You must be logged in to submit a review")
            
        # Add user to the data
        validated_data['user'] = request.user
        # Create review instance
        review = GuestReview.objects.create(**validated_data)
        return review

class AttractionReviewsSerializer(serializers.ModelSerializer):
    reviews = GuestReviewSerializer(many=True, read_only=True)
    review_count = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Attraction
        fields = ['id', 'name', 'reviews', 'review_count', 'avg_rating']
        ref_name = 'WebAttractionReviewsSerializer'
    
    def get_review_count(self, obj):
        # Check if this is for Swagger documentation generation
        if hasattr(self, 'context') and self.context.get('request') and getattr(self.context['request'], 'swagger_fake_view', False):
            return 0
        return obj.reviews.filter(is_published=True).count()
    
    def get_avg_rating(self, obj):
        # Check if this is for Swagger documentation generation
        if hasattr(self, 'context') and self.context.get('request') and getattr(self.context['request'], 'swagger_fake_view', False):
            return 0
        reviews = obj.reviews.filter(is_published=True)
        if not reviews.exists():
            return 0
        total_rating = sum(review.rating for review in reviews)
        return round(total_rating / reviews.count(), 1)

class AttractionSerializer(serializers.ModelSerializer):
    review_count = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    park_name = serializers.CharField(source='park.name', read_only=True)
    destination_name = serializers.CharField(source='park.destination.name', read_only=True)
    
    class Meta:
        model = Attraction
        fields = [
            'id', 'name', 'description', 'image', 
            'park', 'park_name', 'destination_name',
            'timezone', 'entity_type', 'destination_id',
            'attraction_type', 'external_id', 'parent_id',
            'longitude', 'latitude',
            'created_at', 'updated_at', 
            'review_count', 'avg_rating'
        ]
        ref_name = 'WebAttractionSerializer'
    
    def get_review_count(self, obj):
        # Check if this is for Swagger documentation generation
        if hasattr(self, 'context') and self.context.get('request') and getattr(self.context['request'], 'swagger_fake_view', False):
            return 0
        return obj.reviews.filter(is_published=True).count()
    
    def get_avg_rating(self, obj):
        # Check if this is for Swagger documentation generation
        if hasattr(self, 'context') and self.context.get('request') and getattr(self.context['request'], 'swagger_fake_view', False):
            return 0
        reviews = obj.reviews.filter(is_published=True)
        if not reviews.exists():
            return 0
        total_rating = sum(review.rating for review in reviews)
        return round(total_rating / reviews.count(), 1)

