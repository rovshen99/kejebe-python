from rest_framework import mixins, viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.devices.models import Device
from apps.devices.serializers import DeviceCityUpdateSerializer


class DeviceCityViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = DeviceCityUpdateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        device_id = (
            request.headers.get("X-Device-ID")
            or request.headers.get("X-Device-Id")
            or request.data.get("device_id")
        )
        serializer = self.get_serializer(data=request.data, context={"device_id": device_id})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        platform = (
            request.headers.get("X-Platform")
            or request.data.get("platform")
            or Device.Platform.UNKNOWN
        )
        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None

        device, created = Device.objects.get_or_create(
            device_id=validated["device_id"],
            defaults={"platform": platform, "user": user},
        )
        updates = []
        if device.city_id != validated["city"].id:
            device.city = validated["city"]
            updates.append("city")
        if user and device.user_id is None:
            device.user = user
            updates.append("user")
        if updates:
            updates.append("updated_at")
            device.save(update_fields=updates)

        target_user = device.user or user
        if target_user and target_user.city_id != validated["city"].id:
            target_user.city = validated["city"]
            target_user.save(update_fields=["city", "updated_at"])

        return Response(
            {
                "device_id": device.device_id,
                "city": device.city_id,
            },
            status=status.HTTP_200_OK,
        )
