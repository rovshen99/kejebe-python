from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from .models import Banner
from .serializers import BannerSerializer
from core.pagination import CustomPagination


@extend_schema(tags=["Banners"])
class BannerViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = BannerSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['regions', 'cities']
    ordering_fields = ['priority', 'created_at']
    ordering = ['priority', '-created_at']

    def get_queryset(self):
        return Banner.objects.active_now().prefetch_related('regions', 'cities')
