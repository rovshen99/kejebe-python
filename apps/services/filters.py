from django_filters.rest_framework import FilterSet, filters

from apps.services.models import Service


class ServiceFilter(FilterSet):
    region = filters.NumberFilter(field_name="cities__region")
    city = filters.NumberFilter(field_name="cities")

    class Meta:
        model = Service
        fields = ['category', 'is_active', 'tags', 'region', 'city']
