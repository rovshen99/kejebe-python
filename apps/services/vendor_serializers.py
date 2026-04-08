from django.db import transaction
from rest_framework import serializers

from apps.categories.models import Category
from apps.regions.models import City, Region
from apps.services.models import (
    Attribute,
    AttributeOption,
    CategoryAttribute,
    ProductAttributeValue,
    Service,
    ServiceContact,
    ServiceAttributeValue,
    ServiceImage,
    ServiceProduct,
    ServiceProductImage,
    ServiceTag,
    ServiceVideo,
)
from apps.services.serializers import (
    AttributeSerializer,
    CategorySchemaSerializer,
    ServiceContactSerializer,
    ServiceContactWriteSerializer,
    ServiceDetailSerializer,
    ServiceImageSerializer,
    ServiceListSerializer,
    ServiceProductDetailSerializer,
    ServiceProductListSerializer,
    ServiceAttributeValueSerializer,
    ServiceVideoSerializer,
)
from apps.users.models import User
from apps.users.serializers import UserSerializer


class VendorMeSerializer(UserSerializer):
    pass


class VendorMeUpdateSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), allow_null=True, required=False)

    class Meta:
        model = User
        fields = ["name", "surname", "email", "avatar", "city"]


class VendorServiceListSerializer(ServiceListSerializer):
    pass


class VendorServiceDetailSerializer(ServiceDetailSerializer):
    pass


class VendorServiceWriteSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    additional_categories = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), many=True, required=False
    )
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), allow_null=True, required=False)
    available_cities = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), many=True, required=False)
    regions = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), many=True, required=False)
    tags = serializers.PrimaryKeyRelatedField(queryset=ServiceTag.objects.all(), many=True, required=False)
    contacts = ServiceContactWriteSerializer(many=True, required=False)

    class Meta:
        model = Service
        fields = [
            "category",
            "additional_categories",
            "city",
            "available_cities",
            "regions",
            "avatar",
            "background",
            "title_tm",
            "title_ru",
            "description_tm",
            "description_ru",
            "price_min",
            "price_max",
            "discount_text",
            "work_experience_years",
            "address",
            "latitude",
            "longitude",
            "show_location",
            "is_grid_gallery",
            "tags",
            "contacts",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        category = attrs.get("category", getattr(self.instance, "category", None))
        additional_categories = attrs.get("additional_categories")
        if category and additional_categories and category in additional_categories:
            raise serializers.ValidationError(
                {"additional_categories": "Primary category must not be duplicated."}
            )
        if additional_categories and len(additional_categories) > 3:
            raise serializers.ValidationError(
                {"additional_categories": "No more than 3 additional categories are allowed."}
            )
        return attrs

    def _save_relations(self, instance, validated_data):
        additional_categories = validated_data.pop("additional_categories", None)
        available_cities = validated_data.pop("available_cities", None)
        regions = validated_data.pop("regions", None)
        tags = validated_data.pop("tags", None)
        contacts_data = validated_data.pop("contacts", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if additional_categories is not None:
            instance.additional_categories.set(additional_categories)
        if available_cities is not None:
            instance.available_cities.set(available_cities)
        if regions is not None:
            instance.regions.set(regions)
        if tags is not None:
            instance.tags.set(tags)
        if contacts_data is not None:
            instance.contacts.all().delete()
            ServiceContact.objects.bulk_create(
                [ServiceContact(service=instance, **contact_data) for contact_data in contacts_data]
            )
        return instance

    def create(self, validated_data):
        request = self.context["request"]
        instance = Service(vendor=request.user)
        return self._save_relations(instance, validated_data)

    def update(self, instance, validated_data):
        return self._save_relations(instance, validated_data)


class VendorServiceContactSerializer(ServiceContactSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta(ServiceContactSerializer.Meta):
        fields = ["id", "type", "value"]


class VendorServiceContactWriteSerializer(ServiceContactWriteSerializer):
    class Meta(ServiceContactWriteSerializer.Meta):
        fields = ["type_slug", "value"]


class VendorServiceImageSerializer(serializers.ModelSerializer):
    aspect_ratio = serializers.SerializerMethodField()

    class Meta:
        model = ServiceImage
        fields = ["id", "image", "aspect_ratio", "position"]

    def get_aspect_ratio(self, obj):
        return obj.get_or_set_aspect_ratio()


class VendorServiceImageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ["image", "position"]


class VendorServiceVideoSerializer(ServiceVideoSerializer):
    class Meta(ServiceVideoSerializer.Meta):
        fields = ["id", "file", "preview", "hls_url", "hls_ready", "position"]


class VendorServiceVideoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceVideo
        fields = ["file", "preview", "position"]


def _attribute_allowed_for_category(category, attribute, scope):
    return CategoryAttribute.objects.filter(category=category, attribute=attribute, scope=scope).exists()


def _schema_links_map(category, scope):
    return {
        link.attribute_id: link
        for link in CategoryAttribute.objects.select_related("attribute").filter(
            category=category,
            scope=scope,
            attribute__is_active=True,
        )
    }


def _validate_attribute_entries(category, scope, entries, require_complete):
    link_map = _schema_links_map(category, scope)
    seen_ids = set()
    seen_pairs = set()

    for index, attrs in enumerate(entries):
        try:
            _validate_attribute_value_payload(category, scope, attrs)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"items": {index: exc.detail}})

        attribute = attrs["attribute"]
        option = attrs.get("option")

        if attribute.input_type == "multiselect":
            pair = (attribute.id, getattr(option, "id", None))
            if pair in seen_pairs:
                raise serializers.ValidationError(
                    {"items": {index: {"option": "Duplicate multiselect option for the same attribute."}}}
                )
            seen_pairs.add(pair)
        else:
            if attribute.id in seen_ids:
                raise serializers.ValidationError(
                    {"items": {index: {"attribute": "Duplicate attribute in payload."}}}
                )
            seen_ids.add(attribute.id)

    if require_complete:
        missing_links = [
            link for link in link_map.values()
            if link.is_required and link.attribute_id not in seen_ids and link.attribute_id not in {pair[0] for pair in seen_pairs}
        ]
        if missing_links:
            raise serializers.ValidationError(
                {
                    "items": {
                        "required": [
                            link.attribute.slug for link in sorted(missing_links, key=lambda item: item.sort_order)
                        ]
                    }
                }
            )


def _persist_service_attribute_values(service, entries):
    rows = [ServiceAttributeValue(service=service, **item) for item in entries]
    service.service_attribute_values.all().delete()
    if rows:
        ServiceAttributeValue.objects.bulk_create(rows)


def _persist_product_attribute_values(product, entries):
    rows = [ProductAttributeValue(product=product, **item) for item in entries]
    product.values.all().delete()
    if rows:
        ProductAttributeValue.objects.bulk_create(rows)


def _validate_attribute_value_payload(category, scope, attrs):
    attribute = attrs["attribute"]
    option = attrs.get("option")

    if not _attribute_allowed_for_category(category, attribute, scope):
        raise serializers.ValidationError(
            {"attribute": "This attribute is not allowed for the selected category and scope."}
        )

    if option and option.attribute_id != attribute.id:
        raise serializers.ValidationError({"option": "This option does not belong to the selected attribute."})

    if attribute.input_type in {"choice", "multiselect"} and not option:
        raise serializers.ValidationError({"option": "Option is required for choice and multiselect attributes."})

    if attribute.input_type not in {"choice", "multiselect"} and option:
        raise serializers.ValidationError({"option": "Option can only be used for choice and multiselect attributes."})

    if attribute.input_type == "text" and not (attrs.get("value_text_tm") or attrs.get("value_text_ru")):
        raise serializers.ValidationError(
            {"value_text_tm": "Provide localized text value for text attributes."}
        )

    if attribute.input_type == "number" and attrs.get("value_number") is None:
        raise serializers.ValidationError({"value_number": "Provide number value for numeric attributes."})

    if attribute.input_type == "boolean" and attrs.get("value_boolean") is None:
        raise serializers.ValidationError({"value_boolean": "Provide boolean value for boolean attributes."})

    return attrs


class VendorAttributeValueWriteSerializer(serializers.ModelSerializer):
    attribute = serializers.PrimaryKeyRelatedField(queryset=Attribute.objects.all())
    option = serializers.PrimaryKeyRelatedField(queryset=AttributeOption.objects.all(), allow_null=True, required=False)

    class Meta:
        model = ProductAttributeValue
        fields = [
            "attribute",
            "option",
            "value_text_tm",
            "value_text_ru",
            "value_number",
            "value_boolean",
        ]

    def validate(self, attrs):
        service = self.context["service"]
        return _validate_attribute_value_payload(service.category, CategoryAttribute.Scope.PRODUCT, attrs)


class VendorServiceAttributeValueSerializer(ServiceAttributeValueSerializer):
    pass


class VendorServiceAttributeValueWriteSerializer(serializers.ModelSerializer):
    attribute = serializers.PrimaryKeyRelatedField(queryset=Attribute.objects.all())
    option = serializers.PrimaryKeyRelatedField(queryset=AttributeOption.objects.all(), allow_null=True, required=False)

    class Meta:
        model = ServiceAttributeValue
        fields = [
            "attribute",
            "option",
            "value_text_tm",
            "value_text_ru",
            "value_number",
            "value_boolean",
        ]

    def validate(self, attrs):
        service = self.context["service"]
        return _validate_attribute_value_payload(service.category, CategoryAttribute.Scope.SERVICE, attrs)


class VendorServiceAttributeValueBulkSerializer(serializers.Serializer):
    items = VendorServiceAttributeValueWriteSerializer(many=True)

    def validate(self, attrs):
        service = self.context["service"]
        _validate_attribute_entries(service.category, CategoryAttribute.Scope.SERVICE, attrs["items"], require_complete=True)
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        service = kwargs["service"]
        items = self.validated_data["items"]
        _persist_service_attribute_values(service, items)
        return service.service_attribute_values.select_related("attribute", "option").order_by("id")


class VendorServiceProductListSerializer(ServiceProductListSerializer):
    pass


class VendorServiceProductDetailSerializer(ServiceProductDetailSerializer):
    pass


class VendorServiceProductWriteSerializer(serializers.ModelSerializer):
    values = VendorAttributeValueWriteSerializer(many=True, required=False)
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False, allow_empty=True
    )

    class Meta:
        model = ServiceProduct
        fields = [
            "title_tm",
            "title_ru",
            "description_tm",
            "description_ru",
            "price",
            "priority",
            "values",
            "images",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        values_data = attrs.get("values")
        if values_data is not None:
            service = self.context["service"]
            _validate_attribute_entries(service.category, CategoryAttribute.Scope.PRODUCT, values_data, require_complete=True)
        return attrs

    def _save_values(self, product, values_data):
        if values_data is None:
            return
        _persist_product_attribute_values(product, values_data)

    def _save_images(self, product, uploaded_images):
        if not uploaded_images:
            return
        ServiceProductImage.objects.bulk_create(
            [
                ServiceProductImage(product=product, image=image, position=index)
                for index, image in enumerate(uploaded_images)
                if image
            ]
        )

    def create(self, validated_data):
        service = self.context["service"]
        values_data = validated_data.pop("values", None)
        uploaded_images = validated_data.pop("images", [])
        request = self.context.get("request")
        if request is not None:
            request_images = list(request.FILES.getlist("images"))
            if request_images:
                uploaded_images = request_images
        product = ServiceProduct.objects.create(service=service, **validated_data)
        self._save_values(product, values_data)
        self._save_images(product, uploaded_images)
        return product

    def update(self, instance, validated_data):
        values_data = validated_data.pop("values", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._save_values(instance, values_data)
        return instance


class VendorServiceProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProductImage
        fields = ["id", "image", "position"]


class VendorServiceProductImageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProductImage
        fields = ["image", "position"]


class ReorderItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    position = serializers.IntegerField(min_value=0)


class ReorderSerializer(serializers.Serializer):
    items = ReorderItemSerializer(many=True)


class VendorCategoryAttributeSerializer(AttributeSerializer):
    pass


class VendorCategorySchemaSerializer(CategorySchemaSerializer):
    pass


class VendorProductAttributeValueBulkSerializer(serializers.Serializer):
    items = VendorAttributeValueWriteSerializer(many=True)

    def validate(self, attrs):
        service = self.context["service"]
        _validate_attribute_entries(service.category, CategoryAttribute.Scope.PRODUCT, attrs["items"], require_complete=True)
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        product = kwargs["product"]
        items = self.validated_data["items"]
        _persist_product_attribute_values(product, items)
        return product.values.select_related("attribute", "option").order_by("id")
