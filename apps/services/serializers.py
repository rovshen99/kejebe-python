from rest_framework import serializers
from .models import Service, ServiceImage, ServiceVideo, Review, Favorite, ContactType, ServiceContact, ServiceProduct, \
    ServiceProductImage, ServiceTag
from apps.users.models import User


class FavoriteStatusMixin(serializers.Serializer):
    is_favorite = serializers.SerializerMethodField()

    def get_is_favorite(self, obj):
        annotated = getattr(obj, 'is_favorite', None)
        if annotated is not None:
            return bool(annotated)
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if user and user.is_authenticated:
            return obj.favorites.filter(user=user).exists()
        return False


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ['image']


class ServiceVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceVideo
        fields = ['file']


class ServiceProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProductImage
        fields = ['image']


class ServiceTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceTag
        fields = ['id', 'name_en', 'name_tm', 'name_ru']


class ServiceLightSerializer(FavoriteStatusMixin, serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)
    videos = ServiceVideoSerializer(many=True, source='servicevideo_set', read_only=True)
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)
    tags = ServiceTagSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'category', 'avatar', 'images', 'videos',
            'title_tm', 'title_ru', 'title_en', 'is_favorite',
            'price_min', 'price_max', 'tags', 'reviews_count',
            'description_en', 'description_ru', 'description_tm',
        ]


class ContactTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContactType
        fields = ['slug', 'name_tm', 'name_ru', 'name_en', 'icon']


class ServiceContactSerializer(serializers.ModelSerializer):
    type = ContactTypeSerializer()

    class Meta:
        model = ServiceContact
        fields = ['type', 'value']


class ServiceProductSerializer(FavoriteStatusMixin, serializers.ModelSerializer):
    images = ServiceProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceProduct
        fields = [
            'id', 'title_tm', 'title_ru', 'title_en', 'description_tm', 'description_ru', 'description_en', 'price',
            'priority',
            'images', 'is_favorite',
        ]


class ServiceSerializer(FavoriteStatusMixin, serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)
    videos = ServiceVideoSerializer(many=True, source='servicevideo_set', read_only=True)
    contacts = ServiceContactSerializer(many=True, read_only=True)
    products = ServiceProductSerializer(many=True, read_only=True)
    tags = ServiceTagSerializer(many=True, read_only=True)
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'vendor', 'category', 'avatar', 'background',
            'title_tm', 'title_ru', 'title_en',
            'description_tm', 'description_ru', 'description_en',
            'price_min', 'price_max', 'is_catalog',
            'latitude', 'longitude', 'is_active', 'active_until',
            'tags', 'priority', 'created_at', 'updated_at',
            'images', 'videos', 'contacts', 'products', 'reviews_count', 'is_favorite'
        ]


class ReviewUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'uuid',
            'name',
            'surname',
            'avatar',
        ]


class ReviewSerializer(serializers.ModelSerializer):
    user = ReviewUserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'service', 'rating', 'comment', 'created_at']
        read_only_fields = ['user', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'service', 'product']
        read_only_fields = ['user']

    def validate(self, attrs):
        service = attrs.get('service')
        product = attrs.get('product')
        if bool(service) == bool(product):
            raise serializers.ValidationError('Specify either service or product (exactly one).')
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
