from rest_framework import serializers
from core.serializers import LangMixin
from core.utils import localized_value
from .models import Category


class CategorySerializer(LangMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name_tm', 'name_ru', 'name',
            'slug', 'parent', 'image', 'icon', 'priority'
        ]

    def get_name(self, obj):
        return localized_value(obj, "name", lang=self._lang())
