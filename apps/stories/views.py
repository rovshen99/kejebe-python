from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils import timezone
from rest_framework import mixins, viewsets, permissions
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.stories.models import ServiceStory, ServiceStoryView
from apps.stories.serializers import ServiceStorySerializer
from apps.stories.filters import ServiceStoryFilter
from apps.services.permissions import IsVendor
from apps.devices.models import Device
from core.pagination import CustomPagination


class ServiceStoryViewSet(mixins.CreateModelMixin,
                          mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = ServiceStorySerializer
    pagination_class = CustomPagination
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ServiceStoryFilter
    ordering_fields = ['priority', 'starts_at', 'created_at']
    ordering = ['priority', '-starts_at', '-created_at']

    def get_queryset(self):
        qs = ServiceStory.objects.select_related('service', 'service__vendor')
        service_id = self.kwargs.get('service_id') or self.kwargs.get('service_pk')
        if service_id is not None:
            qs = qs.filter(service_id=service_id)

        now = timezone.now()
        qs = qs.filter(is_active=True).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now),
        )
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsVendor()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        service = serializer.validated_data.get('service')
        if not service or service.vendor_id != getattr(self.request.user, 'id', None):
            raise PermissionDenied("You can only add stories to your own service.")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if getattr(instance.service, 'vendor_id', None) != getattr(self.request.user, 'id', None):
            raise PermissionDenied("You can only update your own service stories.")
        new_service = serializer.validated_data.get('service')
        if new_service and new_service.vendor_id != getattr(self.request.user, 'id', None):
            raise PermissionDenied("You can only update your own service stories.")
        serializer.save(service=new_service or instance.service)

    def perform_destroy(self, instance):
        if getattr(instance.service, 'vendor_id', None) != getattr(self.request.user, 'id', None):
            raise PermissionDenied("You can only delete your own service stories.")
        return super().perform_destroy(instance)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._record_view(request, instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @staticmethod
    def _record_view(request, story: ServiceStory):
        user = request.user if request.user.is_authenticated else None

        device_id = (
            request.headers.get("X-Device-ID")
            or request.headers.get("X-Device-Id")
            or request.query_params.get("device_id", "")
        )
        platform = (
            request.headers.get("X-Platform")
            or request.query_params.get("platform")
            or Device.Platform.UNKNOWN
        )

        device = None

        if device_id:
            device, _ = Device.objects.get_or_create(
                device_id=device_id,
                defaults={
                    "platform": platform,
                    "user": user if user else None,
                },
            )
            if user and device.user_id != user.id:
                device.user = user
                device.save(update_fields=["user", "updated_at"])

        if user:
            ServiceStoryView.objects.get_or_create(
                story=story,
                user=user,
                defaults={"device": device},
            )
        else:
            if not device:
                return
            ServiceStoryView.objects.get_or_create(
                story=story,
                device=device,
            )
