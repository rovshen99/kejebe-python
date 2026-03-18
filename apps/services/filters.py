from django_filters.rest_framework import FilterSet, filters

from apps.services.models import Service, ServiceProduct


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


def parse_int_list(raw):
    if raw is None:
        return []

    if isinstance(raw, str):
        parts = raw.split(",")
    elif isinstance(raw, (list, tuple)):
        parts = raw
    else:
        parts = [raw]

    values = []
    for part in parts:
        try:
            values.append(int(str(part).strip()))
        except (TypeError, ValueError):
            continue
    return values


class ServiceFilter(FilterSet):
    region = NumberInFilter(field_name="available_cities__region", lookup_expr="in")
    city = NumberInFilter(field_name="available_cities", lookup_expr="in")
    category = filters.CharFilter(method="filter_category")

    main_city = filters.NumberFilter(field_name="city")

    def filter_category(self, queryset, name, value):
        category_ids = parse_int_list(value)
        return queryset.filter_by_category_ids(category_ids)

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
