from rest_framework import mixins, viewsets
from .models import Category
from .serializers import CategorySerializer
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Categories"])
class CategoryViewSet(mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['parent', 'slug']
    ordering_fields = ['priority', 'name_tm']
    ordering = ['priority']
