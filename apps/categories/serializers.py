from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'name_tm', 'name_ru', 'name_en',
            'slug', 'parent', 'image', 'icon', 'priority'
        ]
