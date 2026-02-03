from rest_framework import serializers
from core.utils import get_lang_code, localized_value
from .models import Banner


class BannerSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = [
            'id',
            'title_tm', 'title_ru', 'title',
            'image', 'regions', 'cities',
            'is_active', 'starts_at', 'ends_at',
            'priority', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_title(self, obj):
        lang = get_lang_code(self.context.get('request'))
        return localized_value(obj, "title", lang=lang)
