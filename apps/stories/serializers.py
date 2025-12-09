from django.db import models
from rest_framework import serializers

from apps.stories.models import ServiceStory


class ServiceStorySerializer(serializers.ModelSerializer):
    views_count = serializers.IntegerField(source='views.count', read_only=True)
    has_seen = serializers.SerializerMethodField()

    class Meta:
        model = ServiceStory
        fields = [
            'id', 'service', 'title', 'caption', 'image',
            'is_active', 'starts_at', 'ends_at', 'priority',
            'views_count', 'has_seen', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'views_count']

    def get_has_seen(self, obj):
        request = self.context.get('request')
        if request is None:
            return False

        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        device_id = (
            request.headers.get("X-Device-ID")
            or request.headers.get("X-Device-Id")
            or request.query_params.get("device_id")
        )

        qs = obj.views.all()
        if user:
            return qs.filter(user=user).exists()
        if device_id:
            return qs.filter(device__device_id=device_id, user__isnull=True).exists()
        return False
