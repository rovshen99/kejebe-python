from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, PolymorphicProxySerializer
from .models import Service, ServiceImage, ServiceVideo, Review, Favorite, ContactType, ServiceContact, ServiceProduct, \
    ServiceProductImage, ServiceTag, ServiceApplication, ServiceApplicationImage, Attribute, AttributeValue
from apps.users.models import User
from apps.accounts.services.phone import normalize_phone
from apps.regions.serializers import CitySerializer


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
    class Meta:
        model = ServiceImage
        fields = ['image']


class ServiceVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceVideo
        fields = ['file']


class ServiceProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProductImage
        fields = ['image']


class ServiceTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceTag
        fields = ['id', 'name_en', 'name_tm', 'name_ru']


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ['id', 'name_tm', 'name_ru', 'name_en', 'slug', 'input_type']


class AttributeValueSerializer(serializers.ModelSerializer):
    attribute = AttributeSerializer(read_only=True)

    class Meta:
        model = AttributeValue
        fields = [
            'attribute',
            'value_text_tm', 'value_text_ru', 'value_text_en',
            'value_number', 'value_boolean',
        ]


class ServiceLightSerializer(FavoriteStatusMixin, serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)
    videos = ServiceVideoSerializer(many=True, source='servicevideo_set', read_only=True)
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)
    tags = ServiceTagSerializer(many=True, read_only=True)
    available_cities = CitySerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'category', 'city', 'address', 'available_cities',
            'avatar', 'images', 'videos',
            'title_tm', 'title_ru', 'title_en', 'is_favorite',
            'price_min', 'price_max', 'tags', 'reviews_count',
            'description_en', 'description_ru', 'description_tm',
        ]


class ContactTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContactType
        fields = ['slug', 'name_tm', 'name_ru', 'name_en', 'icon']


class ServiceContactSerializer(serializers.ModelSerializer):
    type = ContactTypeSerializer()

    class Meta:
        model = ServiceContact
        fields = ['type', 'value']


class ServiceProductSerializer(FavoriteStatusMixin, serializers.ModelSerializer):
    images = ServiceProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceProduct
        fields = [
            'id', 'title_tm', 'title_ru', 'title_en', 'description_tm', 'description_ru', 'description_en', 'price',
            'priority',
            'images', 'is_favorite',
        ]


class ServiceProductDetailSerializer(ServiceProductSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)
    contacts = ServiceContactSerializer(many=True, source='service.contacts', read_only=True)

    class Meta(ServiceProductSerializer.Meta):
        fields = ServiceProductSerializer.Meta.fields + ['values', 'contacts']


class ServiceSerializer(FavoriteStatusMixin, serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, source='serviceimage_set', read_only=True)
    videos = ServiceVideoSerializer(many=True, source='servicevideo_set', read_only=True)
    contacts = ServiceContactSerializer(many=True, read_only=True)
    products = ServiceProductSerializer(many=True, read_only=True)
    tags = ServiceTagSerializer(many=True, read_only=True)
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)
    available_cities = CitySerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'vendor', 'category', 'city', 'address', 'available_cities', 'avatar', 'background',
            'title_tm', 'title_ru', 'title_en',
            'description_tm', 'description_ru', 'description_en',
            'price_min', 'price_max', 'is_catalog',
            'latitude', 'longitude', 'is_active', 'active_until',
            'tags', 'priority', 'created_at', 'updated_at',
            'images', 'videos', 'contacts', 'products', 'reviews_count', 'is_favorite'
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
                ServiceLightSerializer,
                ServiceProductSerializer,
            ],
            many=False,
        )
    )
    def get_object(self, obj):
        request = self.context.get('request')
        if obj.service_id:
            serializer = ServiceLightSerializer(obj.service, context={'request': request})
            return serializer.data
        if obj.product_id:
            serializer = ServiceProductSerializer(obj.product, context={'request': request})
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
            'id', 'category', 'city', 'phone', 'title', 'contact_name', 'description',
            'images', 'images_preview', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'category': {'required': False, 'allow_null': True},
        }

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
