from django.conf import settings
from rest_framework import serializers
from core.utils import get_lang_code, localized_value
from .models import Region, City


class RegionSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    is_default = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ['id', 'name_tm', 'name_ru', 'name_en', 'name', 'is_default']

    def get_name(self, obj):
        lang = get_lang_code(self.context.get('request'))
        return localized_value(obj, "name", lang=lang)

    def get_is_default(self, obj):
        default_region_id = getattr(settings, "DEFAULT_REGION_ID", None)
        return bool(default_region_id and obj.id == default_region_id)


class CitySerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ['id', 'name_tm', 'name_ru', 'name_en', 'name', 'is_region_level', 'region']

    def get_name(self, obj):
        lang = get_lang_code(self.context.get('request'))
        return localized_value(obj, "name", lang=lang)
