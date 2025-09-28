from django_filters.rest_framework import FilterSet, filters

from apps.services.models import Service, ServiceProduct


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


class ServiceFilter(FilterSet):
    region = NumberInFilter(field_name="available_cities__region", lookup_expr="in")
    city = NumberInFilter(field_name="available_cities", lookup_expr="in")
    category = NumberInFilter(field_name="category", lookup_expr="in")

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
