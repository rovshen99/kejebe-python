from rest_framework import serializers
from core.utils import get_lang_code, localized_value
from .models import Region, City


class RegionSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ['id', 'name_tm', 'name_ru', 'name_en', 'name']

    def get_name(self, obj):
        lang = get_lang_code(self.context.get('request'))
        return localized_value(obj, "name", lang=lang)


class CitySerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ['id', 'name_tm', 'name_ru', 'name_en', 'name', 'region']

    def get_name(self, obj):
        lang = get_lang_code(self.context.get('request'))
        return localized_value(obj, "name", lang=lang)
