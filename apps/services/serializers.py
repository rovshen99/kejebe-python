from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from django.core.files.storage import default_storage
from core.serializers import LangMixin
from core.utils import format_price_text, localized_value
from drf_spectacular.utils import extend_schema_field, PolymorphicProxySerializer
from .models import Service, ServiceImage, ServiceVideo, Review, Favorite, ContactType, ServiceContact, ServiceProduct, \
    ServiceProductImage, ServiceApplication, ServiceApplicationImage, ServiceApplicationLink, Attribute, AttributeOption, ProductAttributeValue, CategoryAttribute, ServiceAttributeValue
from apps.users.models import User
from apps.accounts.services.phone import normalize_phone
from apps.regions.serializers import CitySerializer
from apps.regions.models import City

SERVICE_APPLICATION_DUPLICATE_WINDOW = timedelta(hours=12)
SERVICE_APPLICATION_LOCAL_PHONE_LENGTH = 8
SERVICE_APPLICATION_MAX_LINKS = 5


class FavoriteStatusMixin(serializers.Serializer):
    is_favorite = serializers.SerializerMethodField()

    def get_is_favorite(self, obj):
        annotated = getattr(obj, 'is_favorite', None)
        if annotated is not None:
            return bool(annotated)
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if user and user.is_authenticated:
            return obj.favorites.filter(user=user).exists()
        return False


def _get_field_dimensions(file_field):
    if not file_field:
        return None, None
    try:
        from PIL import Image
    except Exception:
        return None, None
    try:
        file_field.open()
        with Image.open(file_field) as img:
            width, height = img.size
            return width, height
    except Exception:
        return None, None
    finally:
        try:
            file_field.close()
        except Exception:
            pass


class ServiceImageSerializer(serializers.ModelSerializer):
    aspect_ratio = serializers.SerializerMethodField()

    class Meta:
        model = ServiceImage
        fields = ['image', 'aspect_ratio']

    def get_aspect_ratio(self, obj):
        return obj.get_or_set_aspect_ratio()


class ServiceVideoSerializer(serializers.ModelSerializer):
    hls_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceVideo
        fields = ['id', 'file', 'preview', 'hls_url', 'hls_ready']

    def get_hls_url(self, obj):
        return obj.get_hls_url()


class ServiceProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProductImage
        fields = ['image']


class AttributeSerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    placeholder = serializers.SerializerMethodField()
    help_text = serializers.SerializerMethodField()

    class Meta:
        model = Attribute
        fields = [
            'id', 'name_tm', 'name_ru', 'name',
            'icon',
            'slug', 'input_type', 'unit_tm', 'unit_ru', 'unit',
            'placeholder_tm', 'placeholder_ru', 'placeholder',
            'help_text_tm', 'help_text_ru', 'help_text',
            'min_value', 'max_value', 'step',
        ]

    def get_name(self, obj):
        return localized_value(obj, "name", lang=self._lang())

    def get_icon(self, obj):
        icon = getattr(obj, "icon", None)
        return getattr(icon, "url", None) if icon else None

    def get_unit(self, obj):
        return localized_value(obj, "unit", lang=self._lang())

    def get_placeholder(self, obj):
        return localized_value(obj, "placeholder", lang=self._lang())

    def get_help_text(self, obj):
        return localized_value(obj, "help_text", lang=self._lang())


class AttributeOptionSerializer(LangMixin, serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = AttributeOption
        fields = ["id", "value", "label_tm", "label_ru", "label"]

    def get_label(self, obj):
        return localized_value(obj, "label", lang=self._lang())


class CategorySchemaAttributeSerializer(LangMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    slug = serializers.CharField(read_only=True)
    name_tm = serializers.CharField(read_only=True)
    name_ru = serializers.CharField(read_only=True)
    name = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    section = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    placeholder = serializers.SerializerMethodField()
    help_text = serializers.SerializerMethodField()
    input_type = serializers.CharField(read_only=True)
    unit_tm = serializers.CharField(read_only=True)
    unit_ru = serializers.CharField(read_only=True)
    placeholder_tm = serializers.CharField(read_only=True)
    placeholder_ru = serializers.CharField(read_only=True)
    help_text_tm = serializers.CharField(read_only=True)
    help_text_ru = serializers.CharField(read_only=True)
    min_value = serializers.FloatField(read_only=True, allow_null=True)
    max_value = serializers.FloatField(read_only=True, allow_null=True)
    step = serializers.FloatField(read_only=True, allow_null=True)
    scope = serializers.CharField(read_only=True)
    section_tm = serializers.CharField(read_only=True)
    section_ru = serializers.CharField(read_only=True)
    is_required = serializers.BooleanField(read_only=True)
    is_filterable = serializers.BooleanField(read_only=True)
    is_highlighted = serializers.BooleanField(read_only=True)
    show_in_filters = serializers.BooleanField(read_only=True)
    show_in_card = serializers.BooleanField(read_only=True)
    show_in_detail = serializers.BooleanField(read_only=True)
    filter_type = serializers.CharField(read_only=True)
    filter_order = serializers.IntegerField(read_only=True)
    sort_order = serializers.IntegerField(read_only=True)
    options = serializers.SerializerMethodField()

    def to_representation(self, instance):
        if isinstance(instance, CategoryAttribute):
            attribute = instance.attribute
            data = {
                "id": attribute.id,
                "slug": attribute.slug,
                "name_tm": attribute.name_tm,
                "name_ru": attribute.name_ru,
                "icon": attribute.icon,
                "input_type": attribute.input_type,
                "unit_tm": attribute.unit_tm,
                "unit_ru": attribute.unit_ru,
                "placeholder_tm": attribute.placeholder_tm,
                "placeholder_ru": attribute.placeholder_ru,
                "help_text_tm": attribute.help_text_tm,
                "help_text_ru": attribute.help_text_ru,
                "min_value": attribute.min_value,
                "max_value": attribute.max_value,
                "step": attribute.step,
                "scope": instance.scope,
                "section_tm": instance.section_tm,
                "section_ru": instance.section_ru,
                "is_required": instance.is_required,
                "is_filterable": instance.is_filterable,
                "is_highlighted": instance.is_highlighted,
                "show_in_filters": instance.show_in_filters,
                "show_in_card": instance.show_in_card,
                "show_in_detail": instance.show_in_detail,
                "filter_type": instance.filter_type,
                "filter_order": instance.filter_order,
                "sort_order": instance.sort_order,
                "options": instance,
            }
            return super().to_representation(data)
        return super().to_representation(instance)

    def get_name(self, obj):
        source = obj.get("options") if isinstance(obj, dict) else obj
        attribute = source.attribute if isinstance(source, CategoryAttribute) else source
        return localized_value(attribute, "name", lang=self._lang())

    def get_icon(self, obj):
        if isinstance(obj, dict):
            icon = obj.get("icon")
            return getattr(icon, "url", None) if icon else None
        source = obj.get("options") if isinstance(obj, dict) else obj
        attribute = source.attribute if isinstance(source, CategoryAttribute) else source
        icon = getattr(attribute, "icon", None)
        return getattr(icon, "url", None) if icon else None

    def get_section(self, obj):
        source = obj.get("section_tm") if isinstance(obj, dict) else obj
        if isinstance(obj, dict):
            if self._lang() == "ru":
                return obj.get("section_ru") or obj.get("section_tm") or ""
            return obj.get("section_tm") or obj.get("section_ru") or ""
        return ""

    def get_unit(self, obj):
        if isinstance(obj, dict):
            if self._lang() == "ru":
                return obj.get("unit_ru") or obj.get("unit_tm") or ""
            return obj.get("unit_tm") or obj.get("unit_ru") or ""
        return ""

    def get_placeholder(self, obj):
        if isinstance(obj, dict):
            if self._lang() == "ru":
                return obj.get("placeholder_ru") or obj.get("placeholder_tm") or ""
            return obj.get("placeholder_tm") or obj.get("placeholder_ru") or ""
        return ""

    def get_help_text(self, obj):
        if isinstance(obj, dict):
            if self._lang() == "ru":
                return obj.get("help_text_ru") or obj.get("help_text_tm") or ""
            return obj.get("help_text_tm") or obj.get("help_text_ru") or ""
        return ""

    def get_options(self, obj):
        source = obj.get("options") if isinstance(obj, dict) else obj
        if isinstance(source, CategoryAttribute):
            attribute = source.attribute
        elif isinstance(source, (list, tuple)):
            return AttributeOptionSerializer(source, many=True, context=self.context).data
        else:
            attribute = source
        options = getattr(attribute, "prefetched_options", None)
        if options is None:
            options = attribute.options.filter(is_active=True).order_by("sort_order", "id")
        return AttributeOptionSerializer(options, many=True, context=self.context).data


class CategorySchemaSerializer(serializers.Serializer):
    service_attributes = serializers.SerializerMethodField()
    product_attributes = serializers.SerializerMethodField()

    def _schema_qs(self, category):
        return (
            category.category_attributes.select_related("attribute")
            .prefetch_related("attribute__options")
            .filter(attribute__is_active=True)
            .order_by("sort_order", "id")
        )

    def _serialize_scope(self, category, scope):
        items = self._schema_qs(category).filter(scope=scope)
        return CategorySchemaAttributeSerializer(items, many=True, context=self.context).data

    def get_service_attributes(self, obj):
        return self._serialize_scope(obj, CategoryAttribute.Scope.SERVICE)

    def get_product_attributes(self, obj):
        return self._serialize_scope(obj, CategoryAttribute.Scope.PRODUCT)


class AttributeValueSerializer(LangMixin, serializers.ModelSerializer):
    attribute_id = serializers.IntegerField(source="attribute.id", read_only=True)
    attribute = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    slug = serializers.CharField(source="attribute.slug", read_only=True)
    input_type = serializers.CharField(source="attribute.input_type", read_only=True)
    unit_tm = serializers.CharField(source="attribute.unit_tm", read_only=True)
    unit_ru = serializers.CharField(source="attribute.unit_ru", read_only=True)
    unit = serializers.SerializerMethodField()
    option_id = serializers.IntegerField(source="option.id", read_only=True, allow_null=True)
    value = serializers.SerializerMethodField()

    class Meta:
        model = ProductAttributeValue
        fields = [
            'attribute_id',
            'attribute',
            'icon',
            'slug',
            'input_type',
            'unit_tm',
            'unit_ru',
            'unit',
            'option_id',
            'value',
        ]

    def get_attribute(self, obj):
        return localized_value(obj.attribute, "name", lang=self._lang())

    def get_icon(self, obj):
        icon = getattr(obj.attribute, "icon", None)
        return getattr(icon, "url", None) if icon else None

    def get_unit(self, obj):
        return localized_value(obj.attribute, "unit", lang=self._lang())

    def get_value(self, obj):
        input_type = getattr(obj.attribute, "input_type", None)
        if input_type in ("choice", "multiselect") and getattr(obj, "option_id", None):
            return localized_value(obj.option, "label", lang=self._lang())
        if input_type == "text":
            return localized_value(obj, "value_text", lang=self._lang())
        if input_type == "number":
            return obj.value_number
        if input_type == "boolean":
            return obj.value_boolean
        return localized_value(obj, "value_text", lang=self._lang())


class ServiceAttributeValueSerializer(LangMixin, serializers.ModelSerializer):
    attribute_id = serializers.IntegerField(source="attribute.id", read_only=True)
    attribute = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    slug = serializers.CharField(source="attribute.slug", read_only=True)
    input_type = serializers.CharField(source="attribute.input_type", read_only=True)
    unit_tm = serializers.CharField(source="attribute.unit_tm", read_only=True)
    unit_ru = serializers.CharField(source="attribute.unit_ru", read_only=True)
    unit = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model = ServiceAttributeValue
        fields = [
            "id",
            "attribute_id",
            "attribute",
            "icon",
            "slug",
            "input_type",
            "unit_tm",
            "unit_ru",
            "unit",
            "value",
        ]

    def get_attribute(self, obj):
        return localized_value(obj.attribute, "name", lang=self._lang())

    def get_icon(self, obj):
        icon = getattr(obj.attribute, "icon", None)
        return getattr(icon, "url", None) if icon else None

    def get_unit(self, obj):
        return localized_value(obj.attribute, "unit", lang=self._lang())

    def get_value(self, obj):
        input_type = getattr(obj.attribute, "input_type", None)
        if input_type in ("choice", "multiselect") and getattr(obj, "option_id", None):
            return localized_value(obj.option, "label", lang=self._lang())
        if input_type == "text":
            return localized_value(obj, "value_text", lang=self._lang())
        if input_type == "number":
            return obj.value_number
        if input_type == "boolean":
            return obj.value_boolean
        return localized_value(obj, "value_text", lang=self._lang())


class ServiceBaseSerializer(LangMixin, FavoriteStatusMixin, serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    primary_category = serializers.IntegerField(source="category_id", read_only=True)
    additional_categories = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    city_title = serializers.SerializerMethodField()
    region_title = serializers.SerializerMethodField()
    category_title = serializers.SerializerMethodField()
    price_text = serializers.SerializerMethodField()
    rating = serializers.FloatField(read_only=True)
    has_discount = serializers.SerializerMethodField()
    discount_text = serializers.SerializerMethodField()
    reviews_count = serializers.IntegerField(read_only=True)
    is_region_level = serializers.SerializerMethodField()
    has_location = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'category', 'primary_category', 'additional_categories', 'categories',
            'city', 'avatar', 'title_tm', 'title_ru',
            'title', 'is_favorite', 'reviews_count', 'is_verified', 'is_vip',
            'city_title', 'region_title', 'category_title',
            'price_text', 'rating', 'has_discount', 'discount_text', 'work_experience_years',
            'is_region_level', 'has_location', 'show_location',
        ]

    def _localized_name(self, obj, prefix):
        return localized_value(obj, prefix, lang=self._lang())

    def get_title(self, obj):
        return localized_value(obj, "title", lang=self._lang())

    def get_city_title(self, obj):
        return self._localized_name(getattr(obj, "city", None), "name")

    def get_region_title(self, obj):
        city = getattr(obj, "city", None)
        return self._localized_name(getattr(city, "region", None), "name")

    def _additional_category_ids(self, obj):
        categories_rel = getattr(obj, "additional_categories", None)
        if categories_rel is None:
            return []
        categories = categories_rel.all() if hasattr(categories_rel, "all") else categories_rel
        return [category.id for category in categories]

    def get_additional_categories(self, obj):
        return self._additional_category_ids(obj)

    def get_categories(self, obj):
        return [obj.category_id, *self._additional_category_ids(obj)]

    def get_category_title(self, obj):
        return self._localized_name(getattr(obj, "category", None), "name")

    def get_price_text(self, obj):
        return format_price_text(
            getattr(obj, "price_min", None),
            getattr(obj, "price_max", None),
            lang=self._lang(),
        )

    def get_has_discount(self, obj):
        return bool(self.get_discount_text(obj))

    def get_discount_text(self, obj):
        return getattr(obj, "discount_text", None)

    def get_is_region_level(self, obj):
        city = getattr(obj, "city", None)
        if not city:
            return False
        return bool(getattr(city, "is_region_level", False))

    def get_has_location(self, obj):
        address = (getattr(obj, "address", "") or "").strip()
        latitude = getattr(obj, "latitude", None)
        longitude = getattr(obj, "longitude", None)
        return bool(address) or (latitude is not None and longitude is not None)


class ServiceCoverUrlMixin(serializers.Serializer):
    cover_url = serializers.SerializerMethodField()

    def get_cover_url(self, obj):
        if getattr(obj, "avatar", None):
            return obj.avatar.url
        if getattr(obj, "background", None):
            return obj.background.url
        cover_image_path = getattr(obj, "cover_image_path", None) or getattr(obj, "cover_image", None)
        if cover_image_path:
            if hasattr(cover_image_path, "url"):
                return cover_image_path.url
            try:
                return default_storage.url(cover_image_path)
            except Exception:
                return None
        images = getattr(obj, "prefetched_images", None) or []
        first_image = images[0] if images else None
        if not first_image and hasattr(obj, "serviceimage_set"):
            first_image = obj.serviceimage_set.all().first()
        return first_image.image.url if first_image and getattr(first_image, "image", None) else None


class ServiceListSerializer(ServiceCoverUrlMixin, ServiceBaseSerializer):
    open = serializers.SerializerMethodField()

    class Meta(ServiceBaseSerializer.Meta):
        fields = ServiceBaseSerializer.Meta.fields + [
            'cover_url',
            'open',
        ]

    def get_open(self, obj):
        return {"type": "service", "service_id": obj.id}


class ServiceTagsMixin(LangMixin, serializers.Serializer):
    tags = serializers.SerializerMethodField()

    def get_tags(self, obj):
        tags_rel = getattr(obj, "tags", None)
        if not tags_rel:
            return []
        tags = tags_rel.all() if hasattr(tags_rel, "all") else tags_rel
        names = []
        for tag in tags:
            name = localized_value(tag, "name", lang=self._lang())
            if name:
                names.append(name)
        return names


class ServiceCarouselSerializer(ServiceCoverUrlMixin, ServiceTagsMixin, ServiceBaseSerializer):
    images = serializers.SerializerMethodField()
    open = serializers.SerializerMethodField()

    class Meta(ServiceBaseSerializer.Meta):
        fields = ServiceBaseSerializer.Meta.fields + [
            'cover_url',
            'tags',
            'images',
            'open',
        ]

    def get_images(self, obj):
        images = getattr(obj, "prefetched_images", None) or []
        if not images and hasattr(obj, "serviceimage_set"):
            images = obj.serviceimage_set.all()
        urls = []
        for image in images:
            img_field = getattr(image, "image", None)
            if img_field and getattr(img_field, "url", None):
                urls.append(img_field.url)
        return urls

    def get_open(self, obj):
        return {"type": "service", "service_id": obj.id}


class ContactTypeSerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = ContactType
        fields = ['slug', 'name_tm', 'name_ru', 'name', 'icon']

    def get_name(self, obj):
        return localized_value(obj, "name", lang=self._lang())


class ServiceContactSerializer(serializers.ModelSerializer):
    type = ContactTypeSerializer()

    class Meta:
        model = ServiceContact
        fields = ['type', 'value']


class ServiceContactWriteSerializer(serializers.ModelSerializer):
    type_slug = serializers.SlugRelatedField(
        source="type",
        slug_field="slug",
        queryset=ContactType.objects.all(),
    )

    class Meta:
        model = ServiceContact
        fields = ['type_slug', 'value']


class ServiceProductSerializer(LangMixin, FavoriteStatusMixin, serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    images = ServiceProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceProduct
        fields = [
            'id', 'title_tm', 'title_ru', 'title',
            'description_tm', 'description_ru', 'description', 'price',
            'priority',
            'images', 'is_favorite',
        ]

    def get_title(self, obj):
        return localized_value(obj, "title", lang=self._lang())

    def get_description(self, obj):
        return localized_value(obj, "description", lang=self._lang())

    def get_videos(self, obj):
        videos = getattr(obj, "hls_videos", None)
        if videos is None:
            videos = obj.servicevideo_set.filter(hls_ready=True)
        return ServiceVideoSerializer(videos, many=True, context=self.context).data


class ServiceProductListSerializer(ServiceProductSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)

    class Meta(ServiceProductSerializer.Meta):
        fields = ServiceProductSerializer.Meta.fields + [
            'values',
        ]


class ServiceProductInServiceSerializer(ServiceProductSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)

    class Meta(ServiceProductSerializer.Meta):
        fields = [
            'id', 'title_tm', 'title_ru', 'title',
            'price', 'priority',
            'images', 'is_favorite', 'values',
        ]


class ServiceProductDetailSerializer(ServiceProductSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)
    contacts = ServiceContactSerializer(many=True, source='service.contacts', read_only=True)
    service_title_tm = serializers.CharField(source='service.title_tm', read_only=True)
    service_title_ru = serializers.CharField(source='service.title_ru', read_only=True)

    class Meta(ServiceProductSerializer.Meta):
        fields = ServiceProductSerializer.Meta.fields + [
            'values', 'contacts',
            'service', 'service_title_tm', 'service_title_ru'
        ]


class ServiceProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProduct
        fields = [
            'title_tm', 'title_ru',
            'description_tm', 'description_ru',
            'price',
        ]


class ServiceDetailSerializer(ServiceCoverUrlMixin, ServiceTagsMixin, ServiceBaseSerializer):
    description = serializers.SerializerMethodField()
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)
    videos = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    contacts = ServiceContactSerializer(many=True, read_only=True)
    attributes = ServiceAttributeValueSerializer(many=True, source="service_attribute_values", read_only=True)
    products = ServiceProductInServiceSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    available_cities = CitySerializer(many=True, read_only=True)

    class Meta(ServiceBaseSerializer.Meta):
        model = Service
        fields = ServiceBaseSerializer.Meta.fields + [
            'vendor', 'address', 'available_cities', 'background', 'cover_url',
            'description_tm', 'description_ru', 'description',
            'price_min', 'price_max', 'is_catalog',
            'latitude', 'longitude', 'is_active', 'active_until',
            'tags', 'priority', 'created_at', 'updated_at',
            'images', 'videos', 'media', 'contacts', 'attributes', 'products',
            'is_grid_gallery',
        ]

    def get_description(self, obj):
        return localized_value(obj, "description", lang=self._lang())


    def get_videos(self, obj):
        videos = getattr(obj, "hls_videos", None)
        if videos is None:
            videos = obj.servicevideo_set.filter(hls_ready=True)
        return ServiceVideoSerializer(videos, many=True, context=self.context).data

    def get_media(self, obj):
        images = list(getattr(obj, "serviceimage_set", None).all()) if hasattr(obj, "serviceimage_set") else []
        videos = getattr(obj, "hls_videos", None)
        if videos is None:
            videos = obj.servicevideo_set.filter(hls_ready=True) if hasattr(obj, "servicevideo_set") else []

        media = []

        for image in images:
            image_field = getattr(image, "image", None)
            url = getattr(image_field, "url", None) if image_field else None
            if not url:
                continue
            width, height = _get_field_dimensions(image_field)
            aspect_ratio = image.get_or_set_aspect_ratio()
            media.append(
                {
                    "id": image.id,
                    "type": "image",
                    "url": url,
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "sort_order": image.position,
                }
            )

        for video in videos:
            preview_field = getattr(video, "preview", None)
            preview_url = getattr(preview_field, "url", None) if preview_field else None
            playback_url = video.get_hls_url()
            if not preview_url or not playback_url:
                continue
            width, height = _get_field_dimensions(preview_field)
            aspect_ratio = round(width / height, 3) if width and height else None
            media.append(
                {
                    "id": video.id,
                    "type": "video",
                    "preview": preview_url,
                    "playback_url": playback_url,
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "sort_order": video.position,
                }
            )

        media.sort(key=lambda item: (item["sort_order"], 0 if item["type"] == "image" else 1, item["id"]))
        return media


class ServiceShowcaseSerializer(ServiceCoverUrlMixin, ServiceTagsMixin, ServiceBaseSerializer):
    description = serializers.SerializerMethodField()
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)
    contacts = ServiceContactSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    available_cities = CitySerializer(many=True, read_only=True)

    class Meta(ServiceBaseSerializer.Meta):
        model = Service
        fields = ServiceBaseSerializer.Meta.fields + [
            'vendor', 'address', 'available_cities', 'background', 'cover_url',
            'description_tm', 'description_ru', 'description',
            'price_min', 'price_max', 'is_catalog',
            'latitude', 'longitude', 'is_active', 'active_until',
            'tags', 'priority', 'created_at', 'updated_at',
            'images', 'contacts',
            'is_grid_gallery',
        ]

    def get_description(self, obj):
        return localized_value(obj, "description", lang=self._lang())


class ServiceUpdateSerializer(serializers.ModelSerializer):
    available_cities = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), many=True, required=False)
    contacts = ServiceContactWriteSerializer(many=True, required=False)

    class Meta:
        model = Service
        fields = [
            'city', 'address', 'available_cities', 'avatar', 'background',
            'show_location',
            'contacts',
            'title_tm', 'title_ru',
            'description_tm', 'description_ru',
            'price_min', 'price_max', 'work_experience_years',
        ]

    def update(self, instance, validated_data):
        contacts_data = validated_data.pop("contacts", None)
        instance = super().update(instance, validated_data)

        if contacts_data is not None:
            instance.contacts.all().delete()
            ServiceContact.objects.bulk_create(
                [
                    ServiceContact(service=instance, **contact_data)
                    for contact_data in contacts_data
                ]
            )

        return instance


class ReviewUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'uuid',
            'name',
            'surname',
            'avatar',
        ]


class ReviewSerializer(serializers.ModelSerializer):
    user = ReviewUserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'service', 'rating', 'comment', 'created_at']
        read_only_fields = ['user', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ['id', 'user', 'service', 'product', 'type', 'object']
        read_only_fields = ['user']

    def get_type(self, obj):
        return 'service' if obj.service_id else 'product'

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name='FavoriteObject',
            resource_type_field_name='type',
            serializers=[
                ServiceListSerializer,
                ServiceProductDetailSerializer,
            ],
            many=False,
        )
    )
    def get_object(self, obj):
        request = self.context.get('request')
        if obj.service_id:
            service = obj.service
            if service is not None:
                if hasattr(obj, "service_rating"):
                    service.rating = obj.service_rating
                if hasattr(obj, "service_reviews_count"):
                    service.reviews_count = obj.service_reviews_count
                if hasattr(obj, "service_cover_image_path"):
                    service.cover_image_path = obj.service_cover_image_path
            serializer = ServiceListSerializer(service, context={'request': request})
            return serializer.data
        if obj.product_id:
            serializer = ServiceProductDetailSerializer(obj.product, context={'request': request})
            return serializer.data
        return None

    def validate(self, attrs):
        service = attrs.get('service')
        product = attrs.get('product')
        if bool(service) == bool(product):
            raise serializers.ValidationError('Specify either service or product (exactly one).')
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ServiceApplicationLinksField(serializers.Field):
    default_error_messages = {
        "invalid": "Expected a list of URLs.",
        "max_items": f"No more than {SERVICE_APPLICATION_MAX_LINKS} links are allowed.",
    }

    def to_representation(self, value):
        links = value.all() if hasattr(value, "all") else value
        return [link.url for link in links]

    def to_internal_value(self, data):
        if data in (None, serializers.empty):
            return []
        if not isinstance(data, list):
            self.fail("invalid")
        if len(data) > SERVICE_APPLICATION_MAX_LINKS:
            self.fail("max_items")
        url_field = serializers.URLField()
        return [url_field.run_validation(item) for item in data]


class ServiceApplicationSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False, allow_empty=True
    )
    links = ServiceApplicationLinksField(
        required=False,
        help_text=f"Optional list of URLs. Maximum {SERVICE_APPLICATION_MAX_LINKS} items.",
    )

    images_preview = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ServiceApplication
        fields = [
            'id', 'category', 'category_name', 'city', 'city_name', 'phone', 'email', 'title', 'contact_name',
            'address', 'price_from', 'work_experience_years', 'description',
            'links',
            'images', 'images_preview', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'category': {'required': False, 'allow_null': True},
            'city': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        city = attrs.get("city")
        city_name = (attrs.get("city_name") or "").strip()
        if not city and not city_name:
            raise serializers.ValidationError({"city": "Provide city or city_name."})
        return attrs

    def validate_phone(self, value: str) -> str:
        normalized = normalize_phone(value)
        if not normalized:
            raise serializers.ValidationError('Invalid phone number')
        cc = getattr(settings, "DEFAULT_PHONE_COUNTRY_CODE", "993")
        expected_length = 1 + len(cc) + SERVICE_APPLICATION_LOCAL_PHONE_LENGTH
        if not normalized.startswith(f"+{cc}") or len(normalized) != expected_length:
            raise serializers.ValidationError("Only Turkmen phone numbers are allowed.")
        recent_duplicate_exists = ServiceApplication.objects.filter(
            phone=normalized,
            created_at__gte=timezone.now() - SERVICE_APPLICATION_DUPLICATE_WINDOW,
        ).exists()
        if recent_duplicate_exists:
            raise serializers.ValidationError(
                'An application with this phone number was already submitted in the last 12 hours.'
            )
        return normalized

    def get_images_preview(self, obj):
        return [
            {'image': getattr(img.image, 'url', None)} for img in obj.images.all()
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        uploaded = validated_data.pop('images', [])
        links_data = validated_data.pop('links', [])
        # Also accept multiple files via request.FILES.getlist('images')
        if request is not None:
            uploaded += list(request.FILES.getlist('images'))

        application = super().create(validated_data)
        links_to_create = [
            ServiceApplicationLink(application=application, url=url)
            for url in links_data
            if url
        ]
        if links_to_create:
            ServiceApplicationLink.objects.bulk_create(links_to_create)
        images_to_create = [
            ServiceApplicationImage(application=application, image=f) for f in uploaded if f
        ]
        if images_to_create:
            ServiceApplicationImage.objects.bulk_create(images_to_create)
        return application
