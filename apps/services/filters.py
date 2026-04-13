from django.db.models import Exists, OuterRef, Q
from django_filters.rest_framework import FilterSet, filters

from apps.services.models import Attribute, Service, ServiceAttributeValue, ServiceProduct


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


SERVICE_ATTRIBUTE_FILTER_PREFIX = "service_attr."
PRODUCT_ATTRIBUTE_FILTER_PREFIX = "product_attr."
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


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


def parse_float_list(raw):
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
            values.append(float(str(part).strip()))
        except (TypeError, ValueError):
            continue
    return values


def _split_filter_values(raw_values):
    values = []
    for raw in raw_values:
        if raw is None:
            continue
        for part in str(raw).split(","):
            value = part.strip()
            if value:
                values.append(value)
    return values


def _parse_bool(raw):
    value = str(raw).strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    return None


def _parse_attribute_filter_specs(query_params, prefix):
    specs = []
    for key in query_params.keys():
        if not key.startswith(prefix):
            continue

        attribute_key = key[len(prefix):]
        operator = "exact"
        if attribute_key.endswith("_min"):
            attribute_key = attribute_key[:-4]
            operator = "min"
        elif attribute_key.endswith("_max"):
            attribute_key = attribute_key[:-4]
            operator = "max"

        if not attribute_key:
            continue

        values = _split_filter_values(query_params.getlist(key))
        if not values:
            continue

        specs.append(
            {
                "attribute_key": attribute_key,
                "operator": operator,
                "values": values,
            }
        )
    return specs


def _resolve_attributes(specs):
    if not specs:
        return {}

    raw_keys = {spec["attribute_key"] for spec in specs}
    attribute_ids = parse_int_list(list(raw_keys))
    attribute_slugs = [key for key in raw_keys if not str(key).isdigit()]

    queryset = Attribute.objects.filter(is_active=True)
    if attribute_ids or attribute_slugs:
        queryset = queryset.filter(Q(id__in=attribute_ids) | Q(slug__in=attribute_slugs))
    else:
        queryset = queryset.none()

    resolved = {}
    for attribute in queryset.order_by("id"):
        resolved.setdefault(str(attribute.id), attribute)
        resolved.setdefault(attribute.slug, attribute)
    return resolved


def _option_filter_q(field_prefix, values):
    option_ids = parse_int_list(values)
    option_value_q = Q(**{f"{field_prefix}option__value__in": values})
    if option_ids:
        option_value_q |= Q(**{f"{field_prefix}option_id__in": option_ids})
    return option_value_q


def _text_filter_q(field_prefix, values):
    query = Q()
    for value in values:
        query |= Q(**{f"{field_prefix}value_text_tm__iexact": value})
        query |= Q(**{f"{field_prefix}value_text_ru__iexact": value})
    return query


def _apply_attribute_condition(queryset, field_prefix, attribute, spec):
    queryset = queryset.filter(**{f"{field_prefix}attribute_id": attribute.id})
    input_type = attribute.input_type
    values = spec["values"]
    operator = spec["operator"]

    if input_type in {"choice", "multiselect"}:
        if operator != "exact":
            return queryset.none()
        return queryset.filter(_option_filter_q(field_prefix, values))

    if input_type == "text":
        if operator != "exact":
            return queryset.none()
        return queryset.filter(_text_filter_q(field_prefix, values))

    if input_type == "boolean":
        if operator != "exact":
            return queryset.none()
        boolean_value = _parse_bool(values[-1])
        if boolean_value is None:
            return queryset.none()
        return queryset.filter(**{f"{field_prefix}value_boolean": boolean_value})

    if input_type == "number":
        number_values = parse_float_list(values)
        if not number_values:
            return queryset.none()
        if operator == "min":
            return queryset.filter(**{f"{field_prefix}value_number__gte": number_values[0]})
        if operator == "max":
            return queryset.filter(**{f"{field_prefix}value_number__lte": number_values[0]})
        return queryset.filter(**{f"{field_prefix}value_number__in": number_values})

    return queryset.none()


def apply_attribute_filters(queryset, query_params):
    service_specs = _parse_attribute_filter_specs(query_params, SERVICE_ATTRIBUTE_FILTER_PREFIX)
    product_specs = _parse_attribute_filter_specs(query_params, PRODUCT_ATTRIBUTE_FILTER_PREFIX)
    resolved_attributes = _resolve_attributes([*service_specs, *product_specs])

    for spec in service_specs:
        attribute = resolved_attributes.get(spec["attribute_key"])
        if attribute is None:
            continue
        matching_values = ServiceAttributeValue.objects.filter(service_id=OuterRef("pk"))
        matching_values = _apply_attribute_condition(matching_values, "", attribute, spec)
        queryset = queryset.filter(Exists(matching_values))

    resolved_product_specs = []
    for spec in product_specs:
        attribute = resolved_attributes.get(spec["attribute_key"])
        if attribute is None:
            continue
        resolved_product_specs.append((spec, attribute))

    if resolved_product_specs:
        matching_products = ServiceProduct.objects.filter(service_id=OuterRef("pk"))
        for spec, attribute in resolved_product_specs:
            matching_products = _apply_attribute_condition(matching_products, "values__", attribute, spec)
        queryset = queryset.filter(Exists(matching_products))

    return queryset


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
