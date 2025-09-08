from django_filters.rest_framework import FilterSet, filters

from apps.services.models import Service, ServiceProduct


class ServiceFilter(FilterSet):
    region = filters.NumberFilter(field_name="available_cities__region")
    city = filters.NumberFilter(field_name="available_cities")
    main_city = filters.NumberFilter(field_name="city")

    class Meta:
        model = Service
        fields = ['category', 'is_active', 'tags', 'region', 'city', 'main_city']


class ServiceProductFilter(FilterSet):
    service = filters.NumberFilter(field_name="service")
    price_min = filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = ServiceProduct
        fields = [
            'service',
            'price_min',
            'price_max',
        ]
