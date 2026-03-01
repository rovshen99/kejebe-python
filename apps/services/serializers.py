from rest_framework import serializers
from django.core.files.storage import default_storage
from core.serializers import LangMixin
from core.utils import format_price_text, localized_value
from drf_spectacular.utils import extend_schema_field, PolymorphicProxySerializer
from .models import Service, ServiceImage, ServiceVideo, Review, Favorite, ContactType, ServiceContact, ServiceProduct, \
    ServiceProductImage, ServiceApplication, ServiceApplicationImage, Attribute, AttributeValue
from apps.users.models import User
from apps.accounts.services.phone import normalize_phone
from apps.regions.serializers import CitySerializer
from apps.regions.models import City


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
        fields = ['file', 'preview', 'hls_url', 'hls_ready']

    def get_hls_url(self, obj):
        return obj.get_hls_url()


class ServiceProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProductImage
        fields = ['image']


class AttributeSerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Attribute
        fields = ['id', 'name_tm', 'name_ru', 'name', 'slug', 'input_type']

    def get_name(self, obj):
        return localized_value(obj, "name", lang=self._lang())


class AttributeValueSerializer(LangMixin, serializers.ModelSerializer):
    attribute = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model = AttributeValue
        fields = [
            'attribute',
            'value',
        ]

    def get_attribute(self, obj):
        return localized_value(obj.attribute, "name", lang=self._lang())

    def get_value(self, obj):
        input_type = getattr(obj.attribute, "input_type", None)
        if input_type in ("text", "choice"):
            return localized_value(obj, "value_text", lang=self._lang())
        if input_type == "number":
            return obj.value_number
        if input_type == "boolean":
            return obj.value_boolean
        return localized_value(obj, "value_text", lang=self._lang())


class ServiceBaseSerializer(LangMixin, FavoriteStatusMixin, serializers.ModelSerializer):
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

    class Meta:
        model = Service
        fields = [
            'id', 'category',
            'avatar', 'title_tm', 'title_ru', 'title', 'is_favorite',
            'reviews_count',
            'is_verified', 'is_vip',
            'city_title', 'region_title', 'category_title',
            'price_text', 'rating', 'has_discount', 'discount_text',
            'is_region_level',
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
    videos = ServiceVideoSerializer(many=True, source='servicevideo_set', read_only=True)
    contacts = ServiceContactSerializer(many=True, read_only=True)
    products = ServiceProductInServiceSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()
    available_cities = CitySerializer(many=True, read_only=True)

    class Meta(ServiceBaseSerializer.Meta):
        model = Service
        fields = ServiceBaseSerializer.Meta.fields + [
            'vendor', 'city', 'address', 'available_cities', 'background', 'cover_url',
            'description_tm', 'description_ru', 'description',
            'price_min', 'price_max', 'is_catalog',
            'latitude', 'longitude', 'is_active', 'active_until',
            'tags', 'priority', 'created_at', 'updated_at',
            'images', 'videos', 'contacts', 'products',
            'is_grid_gallery',
        ]

    def get_description(self, obj):
        return localized_value(obj, "description", lang=self._lang())


class ServiceUpdateSerializer(serializers.ModelSerializer):
    available_cities = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), many=True, required=False)

    class Meta:
        model = Service
        fields = [
            'city', 'address', 'available_cities', 'avatar', 'background',
            'title_tm', 'title_ru',
            'description_tm', 'description_ru',
            'price_min', 'price_max'
        ]


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


class ServiceApplicationSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False, allow_empty=True
    )

    images_preview = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ServiceApplication
        fields = [
            'id', 'category', 'category_name', 'city', 'city_name', 'phone', 'title', 'contact_name', 'description',
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
        return normalized

    def get_images_preview(self, obj):
        return [
            {'image': getattr(img.image, 'url', None)} for img in obj.images.all()
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        uploaded = validated_data.pop('images', [])
        # Also accept multiple files via request.FILES.getlist('images')
        if request is not None:
            uploaded += list(request.FILES.getlist('images'))

        application = super().create(validated_data)
        images_to_create = [
            ServiceApplicationImage(application=application, image=f) for f in uploaded if f
        ]
        if images_to_create:
            ServiceApplicationImage.objects.bulk_create(images_to_create)
        return application
