from rest_framework import serializers

from apps.services.serializers import ContactTypeSerializer
from .models import SystemContact


class SystemContactSerializer(serializers.ModelSerializer):
    type = ContactTypeSerializer()

    class Meta:
        model = SystemContact
        fields = ["id", "type", "value"]
