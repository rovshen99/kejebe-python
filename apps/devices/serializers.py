from rest_framework import serializers

from apps.regions.models import City


class DeviceCityUpdateSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=128, required=False, allow_blank=True)
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    def validate(self, attrs):
        device_id = attrs.get("device_id") or self.context.get("device_id")
        if not device_id:
            raise serializers.ValidationError({"device_id": "device_id is required (header X-Device-ID or payload)."})
        attrs["device_id"] = device_id
        return attrs
