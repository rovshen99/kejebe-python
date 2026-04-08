from rest_framework import serializers

from apps.categories.models import Category
from apps.regions.models import City, Region
from apps.services.models import (
    Attribute,
    AttributeValue,
    Service,
    ServiceContact,
    ServiceImage,
    ServiceProduct,
    ServiceProductImage,
    ServiceTag,
    ServiceVideo,
)
from apps.services.serializers import (
    AttributeSerializer,
    ServiceContactSerializer,
    ServiceContactWriteSerializer,
    ServiceDetailSerializer,
    ServiceImageSerializer,
    ServiceListSerializer,
    ServiceProductDetailSerializer,
    ServiceProductListSerializer,
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


class VendorAttributeValueWriteSerializer(serializers.ModelSerializer):
    attribute = serializers.PrimaryKeyRelatedField(queryset=Attribute.objects.all())

    class Meta:
        model = AttributeValue
        fields = [
            "attribute",
            "value_text_tm",
            "value_text_ru",
            "value_number",
            "value_boolean",
        ]


class VendorServiceProductListSerializer(ServiceProductListSerializer):
    pass


class VendorServiceProductDetailSerializer(ServiceProductDetailSerializer):
    pass


class VendorServiceProductWriteSerializer(serializers.ModelSerializer):
    values = VendorAttributeValueWriteSerializer(many=True, required=False)

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
        ]

    def _save_values(self, product, values_data):
        if values_data is None:
            return
        product.values.all().delete()
        AttributeValue.objects.bulk_create(
            [AttributeValue(product=product, **value_data) for value_data in values_data]
        )

    def create(self, validated_data):
        service = self.context["service"]
        values_data = validated_data.pop("values", None)
        product = ServiceProduct.objects.create(service=service, **validated_data)
        self._save_values(product, values_data)
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
