from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, viewsets

from .models import SystemContact
from .serializers import SystemContactSerializer


@extend_schema(tags=["System"])
class SystemContactViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = SystemContactSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            SystemContact.objects.filter(is_active=True)
            .select_related("type")
            .only("id", "value", "type__slug", "type__name_tm", "type__name_ru", "type__icon", "priority")
            .order_by("priority", "id")
        )
