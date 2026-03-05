from rest_framework import serializers

from apps.services.serializers import ContactTypeSerializer
from .models import SystemContact, SystemAbout


class SystemContactSerializer(serializers.ModelSerializer):
    type = ContactTypeSerializer()

    class Meta:
        model = SystemContact
        fields = ["id", "type", "value"]


class SystemAboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemAbout
        fields = ["id", "about_tm", "about_ru"]
