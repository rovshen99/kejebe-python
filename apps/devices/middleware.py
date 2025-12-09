from django.utils import timezone

from apps.devices.models import Device
from django.conf import settings


class DeviceLastSeenMiddleware:
    LAST_SEEN_THROTTLE_SECONDS = getattr(
        settings, "DEVICE_LAST_SEEN_THROTTLE_SECONDS", 300
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.device = None
        self._process_device(request)
        return self.get_response(request)

    def _process_device(self, request):
        if not getattr(settings, "DEVICE_LAST_SEEN_ENABLED", True):
            return

        device_id = (
            request.headers.get("X-Device-ID")
            or request.headers.get("X-Device-Id")
            or request.GET.get("device_id")
        )
        if not device_id:
            return

        platform = (
            request.headers.get("X-Platform")
            or request.GET.get("platform")
            or Device.Platform.UNKNOWN
        )

        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None

        device, created = Device.objects.get_or_create(
            device_id=device_id,
            defaults={"platform": platform, "user": user},
        )

        request.device = device

        updates = []
        now = timezone.now()

        if (
            device.last_seen_at is None
            or (now - device.last_seen_at).total_seconds() > self.LAST_SEEN_THROTTLE_SECONDS
        ):
            device.last_seen_at = now
            updates.append("last_seen_at")

        if device.platform != platform:
            device.platform = platform
            updates.append("platform")

        if user and device.user_id is None:
            device.user = user
            updates.append("user")

        if updates:
            updates.append("updated_at")
            device.save(update_fields=list(set(updates)))
