from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Prefetch, Q
from django.db.models.functions import Round
from rest_framework import mixins, viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from core.pagination import CustomPagination
from .permissions import IsVendor, IsServiceVendorOwner, IsServiceProductVendorOwner
from .filters import ServiceFilter, ServiceProductFilter
from .models import Service, Review, Favorite, ServiceProduct, ServiceImage
from .serializers import (
    ServiceDetailSerializer,
    ReviewSerializer,
    FavoriteSerializer,
    ServiceListSerializer,
    ServiceProductSerializer,
    ServiceProductListSerializer,
    ServiceProductDetailSerializer,
    ServiceApplicationSerializer,
    ServiceUpdateSerializer,
    ServiceProductUpdateSerializer,
)
from .mixins import FavoriteAnnotateMixin


@extend_schema(tags=["Services"])
class ServiceViewSet(FavoriteAnnotateMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    queryset = Service.objects.select_related('vendor', 'category', 'city').prefetch_related('tags', 'available_cities')
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ServiceFilter
    ordering_fields = ['priority', 'created_at', 'price_min']
    ordering = ['priority']
    search_fields = ['title_tm', 'title_ru', 'title_en']
    pagination_class = CustomPagination
    favorite_field = 'service'
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceListSerializer
        if self.action in ['update', 'partial_update']:
            return ServiceUpdateSerializer
        return ServiceDetailSerializer

    def get_queryset(self):
        prefetches = ['tags']
        if getattr(self, "action", None) == "retrieve":
            prefetches.append('available_cities')
        qs = (
            Service.objects.filter(is_active=True)
            .select_related('vendor', 'category', 'city', 'city__region')
            .prefetch_related(*prefetches)
            .annotate(
                rating=Round(Avg("reviews__rating", filter=Q(reviews__is_approved=True)), 2),
                reviews_count=Count("reviews", filter=Q(reviews__is_approved=True)),
            )
            .order_by('priority', '-created_at')
        )
        if getattr(self, "action", None) == "retrieve":
            products_qs = ServiceProduct.objects.prefetch_related(
                "images", "values__attribute"
            ).order_by("priority", "-created_at")
            qs = qs.prefetch_related(
                Prefetch("products", queryset=products_qs),
                "contacts__type",
            )
        return self.annotate_is_favorite(qs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsVendor(), IsServiceVendorOwner()]
        return [permissions.AllowAny()]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        instance.refresh_from_db()
        output = ServiceDetailSerializer(instance, context={'request': request})
        return Response(output.data)

    @extend_schema(
        summary='List services',
        description=(
            'Supports filtering by multiple cities, regions, and categories. '
            'For multi-select filters provide comma-separated IDs.'
        ),
        parameters=[
            OpenApiParameter(
                name='city',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by available cities (comma-separated IDs), e.g. 1,2,3',
                style='form',
                explode=False,
            ),
            OpenApiParameter(
                name='region',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by regions (comma-separated IDs), e.g. 4,5',
                style='form',
                explode=False,
            ),
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by categories (comma-separated IDs), e.g. 10,11',
                style='form',
                explode=False,
            ),
            OpenApiParameter(
                name='main_city',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by main city (single ID).',
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Search services by title (all languages).',
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="List my services",
        description="Возвращает активные сервисы текущего вендора",
        responses=ServiceListSerializer(many=True),
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="my",
        permission_classes=[permissions.IsAuthenticated, IsVendor],
    )
    def my(self, request, *args, **kwargs):
        qs = (
            Service.objects.filter(is_active=True, vendor=request.user)
            .select_related("vendor", "category", "city")
            .prefetch_related("tags")
            .annotate(
                rating=Round(Avg("reviews__rating", filter=Q(reviews__is_approved=True)), 2),
                reviews_count=Count("reviews", filter=Q(reviews__is_approved=True)),
            )
            .order_by("priority", "-created_at")
        )
        qs = self.annotate_is_favorite(qs)
        page = self.paginate_queryset(qs)
        serializer = ServiceListSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)


@extend_schema(tags=["Reviews"])
class ReviewViewSet(mixins.ListModelMixin,
                    mixins.CreateModelMixin,
                    mixins.DestroyModelMixin,
                    viewsets.GenericViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['service', 'user']
    pagination_class = CustomPagination

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
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    pagination_class = CustomPagination

    @extend_schema(
        summary='List favorites',
        description=(
            'Returns favorites of the current user. Optional `type` query parameter filters '
            'by target type.'
        ),
        parameters=[
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=['service', 'product'],
                description='Filter favorites by type: service or product.'
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            Favorite.objects.filter(user=self.request.user)
            .select_related(
                'service',
                'service__category',
                'service__city',
                'service__city__region',
                'product',
                'product__service',
            )
            .prefetch_related(
                'service__tags',
            )
            .annotate(
                service_rating=Round(
                    Avg(
                    "service__reviews__rating",
                    filter=Q(service__reviews__is_approved=True),
                    ),
                    2,
                ),
                service_reviews_count=Count(
                    "service__reviews",
                    filter=Q(service__reviews__is_approved=True),
                ),
            )
        )
        fav_type = (self.request.query_params.get('type') or '').lower().strip()
        if fav_type == 'service':
            qs = qs.filter(service__isnull=False, product__isnull=True)
        elif fav_type == 'product':
            qs = qs.filter(product__isnull=False, service__isnull=True)
        return qs

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("You can only delete your own favorites.")
        instance.delete()

    @extend_schema(
        summary='Delete favorite by service/product',
        description=(
            'Deletes a favorite for the current user by target identifier. '
            'Provide either `service` or `product` as a query parameter.'
        ),
        parameters=[
            OpenApiParameter(
                name='service',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Service ID to delete from favorites (mutually exclusive with `product`).'
            ),
            OpenApiParameter(
                name='product',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Product ID to delete from favorites (mutually exclusive with `service`).'
            ),
        ],
        responses={
            204: None,
            400: OpenApiResponse(description='Provide only one of service or product.'),
            404: OpenApiResponse(description='Not found.'),
        },
    )
    @action(detail=False, methods=['delete'], url_path='by-target')
    def delete_by_target(self, request, *args, **kwargs):
        service_id = request.query_params.get('service') or request.query_params.get('service_id')
        product_id = request.query_params.get('product') or request.query_params.get('product_id')

        if not service_id and not product_id:
            return Response({'detail': 'Provide one of service or product.'}, status=status.HTTP_400_BAD_REQUEST)

        if service_id and product_id:
            return Response({'detail': 'Provide only one of service or product.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if service_id:
                instance = Favorite.objects.get(user=request.user, service_id=service_id)
            else:
                instance = Favorite.objects.get(user=request.user, product_id=product_id)
        except Favorite.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, instance)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Service Products"])
class ServiceProductViewSet(FavoriteAnnotateMixin,
                            mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            viewsets.GenericViewSet):
    queryset = ServiceProduct.objects.select_related('service').prefetch_related(
        'images', 'values__attribute', 'service__contacts__type'
    )
    serializer_class = ServiceProductSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ServiceProductFilter
    ordering_fields = ['price', 'created_at', 'priority']
    ordering = ['priority', '-created_at']
    search_fields = ['title_tm', 'title_ru', 'title_en', 'description_tm', 'description_ru', 'description_en']
    favorite_field = 'product'

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(service__is_active=True)
        qs = self.annotate_is_favorite(qs)
        service_id = self.kwargs.get('service_id') or self.kwargs.get('service_pk')
        if service_id is not None:
            qs = qs.filter(service_id=service_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ServiceProductDetailSerializer
        if self.action in ['list', 'my']:
            return ServiceProductListSerializer
        if self.action in ['update', 'partial_update']:
            return ServiceProductUpdateSerializer
        return ServiceProductSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsVendor(), IsServiceProductVendorOwner()]
        return [permissions.AllowAny()]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        instance.refresh_from_db()
        output = ServiceProductDetailSerializer(instance, context={'request': request})
        return Response(output.data)

    @extend_schema(
        summary="List my products",
        description="Возвращает продукты, принадлежащие активным сервисам текущего вендора",
        responses=ServiceProductSerializer(many=True),
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="my",
        permission_classes=[permissions.IsAuthenticated, IsVendor],
    )
    def my(self, request, *args, **kwargs):
        qs = (
            self.get_queryset()
            .filter(service__vendor=request.user, service__is_active=True)
            .order_by("priority", "-created_at")
        )
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


@extend_schema(tags=["Service Applications"])
class ServiceApplicationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ServiceApplicationSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
