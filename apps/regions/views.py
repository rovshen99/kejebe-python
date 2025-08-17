from rest_framework import viewsets, mixins
from .models import Region, City
from .serializers import RegionSerializer, CitySerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Regions"])
class RegionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['name_tm']
    ordering = ['name_tm']


@extend_schema(tags=["Cities"])
class CityViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = City.objects.select_related('region').all()
    serializer_class = CitySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['region']
    ordering_fields = ['name_tm']
    ordering = ['name_tm']
