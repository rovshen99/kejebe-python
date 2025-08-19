from rest_framework import serializers
from .models import Service, ServiceImage, ServiceVideo


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ['url']


class ServiceVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceVideo
        fields = ['url']


class ServiceSerializer(serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)
    videos = ServiceVideoSerializer(many=True, source='servicevideo_set', read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'vendor', 'category', 'avatar',
            'title_tm', 'title_ru', 'title_en',
            'description_tm', 'description_ru', 'description_en',
            'price_min', 'price_max', 'is_catalog',
            'latitude', 'longitude', 'is_active', 'active_until',
            'tags', 'priority', 'created_at', 'updated_at',
            'images', 'videos',
        ]
