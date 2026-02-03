from rest_framework import serializers
from core.utils import get_lang_code, localized_value
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name_tm', 'name_ru', 'name',
            'slug', 'parent', 'image', 'icon', 'priority'
        ]

    def get_name(self, obj):
        lang = get_lang_code(self.context.get('request'))
        return localized_value(obj, "name", lang=lang)
