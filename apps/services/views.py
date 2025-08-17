from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from .models import Service
from .serializers import ServiceSerializer


@extend_schema(tags=["Services"])
class ServiceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Service.objects.select_related('vendor', 'category').prefetch_related('tags')
    serializer_class = ServiceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['category', 'is_active', 'tags']
    ordering_fields = ['priority', 'created_at', 'price_min']
    ordering = ['priority']
