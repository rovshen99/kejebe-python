from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from core.serializers import LangMixin
from core.utils import localized_value
from .models import Category


class CategorySerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    image_thumb = serializers.SerializerMethodField(
        help_text="Recommended thumbnail URL for mobile category cards (480x360 WebP).",
    )

    class Meta:
        model = Category
        fields = [
            'id', 'name_tm', 'name_ru', 'name',
            'slug', 'parent', 'image', 'image_thumb', 'icon', 'priority'
        ]

    def get_name(self, obj):
        return localized_value(obj, "name", lang=self._lang())

    @extend_schema_field(OpenApiTypes.URI)
    def get_image_thumb(self, obj):
        return obj.get_image_thumb_url()
