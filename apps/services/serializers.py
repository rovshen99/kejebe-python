from rest_framework import serializers
from .models import Service, ServiceImage, ServiceVideo, Review, Favorite, ContactType, ServiceContact, ServiceProduct, \
    ServiceProductImage


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


class ServiceLightSerializer(serializers.ModelSerializer):
    images = ServiceProductImageSerializer(many=True, read_only=True)
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'vendor', 'category', 'avatar',
            'title_tm', 'title_ru', 'title_en',
            'price_min', 'price_max', 'tags', 'images',
            'is_favorite', 'reviews_count',
        ]

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False


class ContactTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactType
        fields = ['slug', 'name_tm', 'name_ru', 'name_en', 'icon']


class ServiceContactSerializer(serializers.ModelSerializer):
    type = ContactTypeSerializer()

    class Meta:
        model = ServiceContact
        fields = ['type', 'value']


class ServiceProductSerializer(serializers.ModelSerializer):
    images = ServiceProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceProduct
        fields = [
            'id', 'title_tm', 'title_ru', 'title_en', 'description_tm', 'description_ru', 'description_en', 'price',
            'images',
        ]


class ServiceSerializer(serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)
    videos = ServiceVideoSerializer(many=True, source='servicevideo_set', read_only=True)
    contacts = ServiceContactSerializer(many=True, read_only=True)
    products = ServiceProductSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'vendor', 'category', 'avatar',
            'title_tm', 'title_ru', 'title_en',
            'description_tm', 'description_ru', 'description_en',
            'price_min', 'price_max', 'is_catalog',
            'latitude', 'longitude', 'is_active', 'active_until',
            'tags', 'priority', 'created_at', 'updated_at',
            'images', 'videos', 'contacts', 'products'
        ]


class ReviewSerializer(serializers.ModelSerializer):
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
        fields = ['id', 'user', 'service']
        read_only_fields = ['user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
