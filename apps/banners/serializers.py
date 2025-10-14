from rest_framework import serializers

from .models import Banner


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = [
            'id',
            'title_tm', 'title_ru', 'title_en',
            'image', 'link_url', 'service',
            'regions', 'cities',
            'is_active', 'starts_at', 'ends_at',
            'priority', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
