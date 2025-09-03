from django.core.exceptions import PermissionDenied
from rest_framework import mixins, viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from core.pagination import CustomPagination
from .filters import ServiceFilter, ServiceProductFilter
from .models import Service, Review, Favorite, ServiceProduct
from .serializers import ServiceSerializer, ReviewSerializer, FavoriteSerializer, ServiceLightSerializer, ServiceProductSerializer


@extend_schema(tags=["Services"])
class ServiceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Service.objects.select_related('vendor', 'category').prefetch_related('tags')
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ServiceFilter
    ordering_fields = ['priority', 'created_at', 'price_min']
    ordering = ['priority']
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceLightSerializer
        return ServiceSerializer

    def get_queryset(self):
        return Service.objects.filter(is_active=True) \
            .select_related('vendor', 'category') \
            .prefetch_related('tags') \
            .order_by('priority', '-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(tags=["Reviews"])
class ReviewViewSet(mixins.ListModelMixin,
                    mixins.CreateModelMixin,
                    mixins.DestroyModelMixin,
                    viewsets.GenericViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['service', 'user']

    def get_queryset(self):
        return Review.objects.filter(is_approved=True).select_related('user', 'service')

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("You can only delete your own review.")
        instance.delete()


@extend_schema(tags=["Favorites"])
class FavoriteViewSet(mixins.ListModelMixin,
                      mixins.CreateModelMixin,
                      mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    queryset = Favorite.objects.select_related('user', 'service')
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['service', 'user']

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('service')

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("You can only delete your own favorites.")
        instance.delete()


@extend_schema(tags=["Service Products"])
class ServiceProductViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    queryset = ServiceProduct.objects.select_related('service').prefetch_related('images')
    serializer_class = ServiceProductSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ServiceProductFilter
    ordering_fields = ['price', 'created_at', 'priority']
    ordering = ['priority', '-created_at']
    search_fields = ['title_tm', 'title_ru', 'title_en', 'description_tm', 'description_ru', 'description_en']

    def get_queryset(self):
        qs = super().get_queryset()
        service_id = self.kwargs.get('service_id') or self.kwargs.get('service_pk')
        if service_id is not None:
            qs = qs.filter(service_id=service_id)
        return qs
