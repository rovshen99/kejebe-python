from django.db.models import Avg, Count, OuterRef, Q, Subquery
from django.db.models.functions import Round
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.services.filters import ServiceProductFilter
from apps.services.mixins import FavoriteAnnotateMixin
from apps.categories.models import Category
from apps.services.models import Attribute, CategoryAttribute, Service, ServiceAttributeValue, ServiceImage, ServiceProduct, ServiceProductImage, ServiceVideo
from apps.services.permissions import IsVendor
from apps.services.serializers import CategorySchemaSerializer, ServiceDetailSerializer
from apps.services.vendor_serializers import (
    ReorderSerializer,
    VendorCategoryAttributeSerializer,
    VendorCategorySchemaSerializer,
    VendorMeSerializer,
    VendorMeUpdateSerializer,
    VendorProductAttributeValueBulkSerializer,
    VendorServiceAttributeValueBulkSerializer,
    VendorServiceAttributeValueSerializer,
    VendorServiceAttributeValueWriteSerializer,
    VendorServiceContactSerializer,
    VendorServiceContactWriteSerializer,
    VendorServiceDetailSerializer,
    VendorServiceImageSerializer,
    VendorServiceImageWriteSerializer,
    VendorServiceListSerializer,
    VendorServiceProductDetailSerializer,
    VendorServiceProductImageSerializer,
    VendorServiceProductImageWriteSerializer,
    VendorServiceProductListSerializer,
    VendorServiceProductWriteSerializer,
    VendorServiceVideoSerializer,
    VendorServiceVideoWriteSerializer,
    VendorServiceWriteSerializer,
)
from apps.users.serializers import UserSerializer
from core.pagination import CustomPagination


class VendorOwnedServiceMixin:
    def get_vendor_service(self):
        return get_object_or_404(Service, pk=self.kwargs["service_pk"], vendor=self.request.user)


class VendorOwnedProductMixin(VendorOwnedServiceMixin):
    def get_vendor_product(self):
        return get_object_or_404(
            ServiceProduct,
            pk=self.kwargs["product_pk"],
            service_id=self.kwargs["service_pk"],
            service__vendor=self.request.user,
        )


class VendorMeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get(self, request):
        serializer = VendorMeSerializer(request.user, context={"request": request})
        return Response(serializer.data)


class VendorMeUpdateView(generics.UpdateAPIView):
    serializer_class = VendorMeUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        return Response(UserSerializer(instance, context={"request": request}).data)


class VendorServiceViewSet(FavoriteAnnotateMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = CustomPagination
    favorite_field = "service"

    def get_queryset(self):
        qs = (
            Service.objects.filter(vendor=self.request.user)
            .select_related("vendor", "category", "city", "city__region")
            .prefetch_related("additional_categories")
            .annotate(
                rating=Round(Avg("reviews__rating", filter=Q(reviews__is_approved=True)), 2),
                reviews_count=Count("reviews", filter=Q(reviews__is_approved=True)),
                cover_image_path=Subquery(
                    ServiceImage.objects.filter(service_id=OuterRef("pk")).order_by("position", "id").values("image")[:1]
                ),
            )
            .order_by("-created_at")
        )
        if self.action in {"retrieve", "update", "partial_update"}:
            qs = qs.prefetch_related(
                "tags",
                "available_cities",
                "contacts__type",
                "service_attribute_values__attribute",
                "service_attribute_values__option",
            )
        if self.action == "retrieve":
            qs = qs.prefetch_related(
                "products__values__attribute",
                "products__values__option",
                "products__images",
                "serviceimage_set",
                "servicevideo_set",
            )
        return self.annotate_is_favorite(qs)

    def get_serializer_class(self):
        if self.action == "list":
            return VendorServiceListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return VendorServiceWriteSerializer
        return VendorServiceDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        output = VendorServiceDetailSerializer(instance, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.refresh_from_db()
        return Response(VendorServiceDetailSerializer(instance, context={"request": request}).data)


class VendorServiceContactViewSet(VendorOwnedServiceMixin,
                                  mixins.ListModelMixin,
                                  mixins.CreateModelMixin,
                                  mixins.UpdateModelMixin,
                                  mixins.DestroyModelMixin,
                                  viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = None

    def get_queryset(self):
        service = self.get_vendor_service()
        return service.contacts.select_related("type").order_by("id")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return VendorServiceContactWriteSerializer
        return VendorServiceContactSerializer

    def create(self, request, *args, **kwargs):
        service = self.get_vendor_service()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save(service=service)
        return Response(VendorServiceContactSerializer(contact, context={"request": request}).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        return Response(VendorServiceContactSerializer(contact, context={"request": request}).data)


class VendorServiceAttributeValueViewSet(VendorOwnedServiceMixin,
                                         mixins.ListModelMixin,
                                         mixins.CreateModelMixin,
                                         mixins.UpdateModelMixin,
                                         mixins.DestroyModelMixin,
                                         viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = None

    def get_queryset(self):
        return ServiceAttributeValue.objects.filter(
            service_id=self.kwargs["service_pk"],
            service__vendor=self.request.user,
        ).select_related("attribute", "option").order_by("id")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return VendorServiceAttributeValueWriteSerializer
        return VendorServiceAttributeValueSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["service"] = self.get_vendor_service()
        return context

    def create(self, request, *args, **kwargs):
        service = self.get_vendor_service()
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        value = serializer.save(service=service)
        return Response(VendorServiceAttributeValueSerializer(value, context={"request": request}).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        value = serializer.save()
        return Response(VendorServiceAttributeValueSerializer(value, context={"request": request}).data)

    @action(detail=False, methods=["put"], url_path="bulk")
    def bulk(self, request, service_pk=None):
        service = self.get_vendor_service()
        serializer = VendorServiceAttributeValueBulkSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        values = serializer.save(service=service)
        return Response(VendorServiceAttributeValueSerializer(values, many=True, context={"request": request}).data)

class VendorServiceImageViewSet(VendorOwnedServiceMixin,
                                mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = None

    def get_queryset(self):
        return ServiceImage.objects.filter(
            service_id=self.kwargs["service_pk"],
            service__vendor=self.request.user,
        ).order_by("position", "id")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return VendorServiceImageWriteSerializer
        return VendorServiceImageSerializer

    def create(self, request, *args, **kwargs):
        service = self.get_vendor_service()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.save(service=service)
        return Response(VendorServiceImageSerializer(image, context={"request": request}).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        image = serializer.save()
        return Response(VendorServiceImageSerializer(image, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request, service_pk=None):
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]
        images = {image.id: image for image in self.get_queryset().filter(id__in=[item["id"] for item in items])}
        for item in items:
            image = images.get(item["id"])
            if image:
                image.position = item["position"]
                image.save(update_fields=["position"])
        return Response(VendorServiceImageSerializer(self.get_queryset(), many=True, context={"request": request}).data)


class VendorServiceVideoViewSet(VendorOwnedServiceMixin,
                                mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = None

    def get_queryset(self):
        return ServiceVideo.objects.filter(
            service_id=self.kwargs["service_pk"],
            service__vendor=self.request.user,
        ).order_by("position", "id")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return VendorServiceVideoWriteSerializer
        return VendorServiceVideoSerializer

    def create(self, request, *args, **kwargs):
        service = self.get_vendor_service()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video = serializer.save(service=service)
        return Response(VendorServiceVideoSerializer(video, context={"request": request}).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        video = serializer.save()
        return Response(VendorServiceVideoSerializer(video, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request, service_pk=None):
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]
        videos = {video.id: video for video in self.get_queryset().filter(id__in=[item["id"] for item in items])}
        for item in items:
            video = videos.get(item["id"])
            if video:
                video.position = item["position"]
                video.save(update_fields=["position"])
        return Response(VendorServiceVideoSerializer(self.get_queryset(), many=True, context={"request": request}).data)


class VendorServiceProductViewSet(FavoriteAnnotateMixin,
                                  VendorOwnedServiceMixin,
                                  mixins.ListModelMixin,
                                  mixins.CreateModelMixin,
                                  mixins.RetrieveModelMixin,
                                  mixins.UpdateModelMixin,
                                  mixins.DestroyModelMixin,
                                  viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = CustomPagination
    filterset_class = ServiceProductFilter
    favorite_field = "product"

    def get_queryset(self):
        qs = (
            ServiceProduct.objects.filter(
                service_id=self.kwargs["service_pk"],
                service__vendor=self.request.user,
            )
            .select_related("service")
            .prefetch_related("images", "values__attribute", "values__option", "service__contacts__type")
            .order_by("priority", "-created_at")
        )
        return self.annotate_is_favorite(qs)

    def get_serializer_class(self):
        if self.action == "list":
            return VendorServiceProductListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return VendorServiceProductWriteSerializer
        return VendorServiceProductDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        if self.action in {"create", "update", "partial_update"}:
            context["service"] = self.get_vendor_service()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(VendorServiceProductDetailSerializer(product, context={"request": request}).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        product.refresh_from_db()
        return Response(VendorServiceProductDetailSerializer(product, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request, service_pk=None):
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]
        products = {product.id: product for product in self.get_queryset().filter(id__in=[item["id"] for item in items])}
        for item in items:
            product = products.get(item["id"])
            if product:
                product.priority = item["position"]
                product.save(update_fields=["priority"])
        return Response(VendorServiceProductListSerializer(self.get_queryset(), many=True, context={"request": request}).data)

    @action(detail=True, methods=["put"], url_path="attributes/bulk")
    def bulk_attributes(self, request, service_pk=None, pk=None):
        product = self.get_object()
        serializer = VendorProductAttributeValueBulkSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        values = serializer.save(product=product)
        return Response(VendorServiceProductDetailSerializer(product, context={"request": request}).data)


class VendorServiceProductImageViewSet(VendorOwnedProductMixin,
                                       mixins.ListModelMixin,
                                       mixins.CreateModelMixin,
                                       mixins.UpdateModelMixin,
                                       mixins.DestroyModelMixin,
                                       viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = None

    def get_queryset(self):
        return ServiceProductImage.objects.filter(
            product_id=self.kwargs["product_pk"],
            product__service_id=self.kwargs["service_pk"],
            product__service__vendor=self.request.user,
        ).order_by("position", "id")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return VendorServiceProductImageWriteSerializer
        return VendorServiceProductImageSerializer

    def create(self, request, *args, **kwargs):
        product = self.get_vendor_product()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.save(product=product)
        return Response(VendorServiceProductImageSerializer(image, context={"request": request}).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        image = serializer.save()
        return Response(VendorServiceProductImageSerializer(image, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request, service_pk=None, product_pk=None):
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]
        images = {image.id: image for image in self.get_queryset().filter(id__in=[item["id"] for item in items])}
        for item in items:
            image = images.get(item["id"])
            if image:
                image.position = item["position"]
                image.save(update_fields=["position"])
        return Response(VendorServiceProductImageSerializer(self.get_queryset(), many=True, context={"request": request}).data)


class VendorCategoryAttributesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get(self, request, category_id):
        category_attributes = (
            CategoryAttribute.objects.select_related("attribute")
            .filter(category_id=category_id, scope=CategoryAttribute.Scope.PRODUCT, attribute__is_active=True)
            .order_by("sort_order", "id")
        )
        payload = [item.attribute for item in category_attributes]
        return Response(VendorCategoryAttributeSerializer(payload, many=True, context={"request": request}).data)


class VendorCategorySchemaView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get(self, request, category_id):
        category = get_object_or_404(Category, pk=category_id)
        serializer = VendorCategorySchemaSerializer(category, context={"request": request})
        return Response(serializer.data)
