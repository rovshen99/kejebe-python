from rest_framework import serializers

from apps.regions.models import City, Region


class DeviceCityUpdateSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=128, required=False, allow_blank=True)
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)
    region = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), required=False, allow_null=True)

    def validate(self, attrs):
        device_id = attrs.get("device_id") or self.context.get("device_id")
        if not device_id:
            raise serializers.ValidationError({"device_id": "device_id is required (header X-Device-ID or payload)."})
        attrs["device_id"] = device_id
        if not attrs.get("city") and not attrs.get("region"):
            raise serializers.ValidationError({"non_field_errors": "city or region is required."})
        return attrs
