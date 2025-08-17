from rest_framework import serializers
from .models import Region, City


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name_tm', 'name_ru', 'name_en']


class CitySerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name_tm', 'name_ru', 'name_en', 'region']
