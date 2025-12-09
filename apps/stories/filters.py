from django_filters.rest_framework import FilterSet, filters
from django.utils import timezone
from django.db import models

from apps.stories.models import ServiceStory


class ServiceStoryFilter(FilterSet):
    service = filters.NumberFilter(field_name="service")
    active_now = filters.BooleanFilter(method='filter_active_now')

    class Meta:
        model = ServiceStory
        fields = [
            'service',
            'is_active',
            'active_now',
        ]

    def filter_active_now(self, queryset, name, value):
        if not value:
            return queryset
        now = timezone.now()
        return queryset.filter(
            is_active=True
        ).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now),
        )
