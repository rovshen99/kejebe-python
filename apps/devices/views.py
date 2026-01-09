from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.devices.models import Device
from apps.devices.serializers import DeviceCityUpdateSerializer


class DeviceCityViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = DeviceCityUpdateSerializer
    permission_classes = [AllowAny]

    @staticmethod
    def _resolve_device_id(request):
        return (
            request.headers.get("X-Device-ID")
            or request.headers.get("X-Device-Id")
            or request.query_params.get("device_id")
            or request.data.get("device_id")
        )

    def create(self, request, *args, **kwargs):
        device_id = self._resolve_device_id(request)
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
        city = validated.get("city")
        region = validated.get("region")
        if city:
            region = city.region

        if device.city_id != (city.id if city else None):
            device.city = city
            updates.append("city")
        if device.region_id != (region.id if region else None):
            device.region = region
            updates.append("region")
        if user and device.user_id is None:
            device.user = user
            updates.append("user")
        if updates:
            updates.append("updated_at")
            device.save(update_fields=updates)

        target_user = device.user or user
        if target_user and city and target_user.city_id != city.id:
            target_user.city = validated["city"]
            target_user.save(update_fields=["city", "updated_at"])

        return Response(
            {
                "device_id": device.device_id,
                "city": device.city_id,
                "region": device.region_id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def retrieve_device(self, request, *args, **kwargs):
        device_id = self._resolve_device_id(request)
        if not device_id:
            return Response({"detail": "device_id is required (header X-Device-ID/X-Device-Id or query param)."}, status=status.HTTP_400_BAD_REQUEST)

        device = Device.objects.filter(device_id=device_id).first()
        if not device:
            return Response({"detail": "Device not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "device_id": device.device_id,
                "city": device.city_id,
                "region": device.region_id,
            },
            status=status.HTTP_200_OK,
        )
