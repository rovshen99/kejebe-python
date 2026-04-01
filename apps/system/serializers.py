from rest_framework import serializers

from apps.services.serializers import ContactTypeSerializer
from apps.accounts.services.phone import normalize_phone
from .models import SystemContact, SystemAbout, ClientFeedback


class SystemContactSerializer(serializers.ModelSerializer):
    type = ContactTypeSerializer()

    class Meta:
        model = SystemContact
        fields = ["id", "type", "value"]


class SystemAboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemAbout
        fields = ["id", "about_tm", "about_ru"]


class MapConfigSerializer(serializers.Serializer):
    tile_url = serializers.CharField()
    attribution = serializers.CharField()
    min_zoom = serializers.IntegerField()
    max_zoom = serializers.IntegerField()


class ClientFeedbackSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source="message")

    class Meta:
        model = ClientFeedback
        fields = ["id", "name", "phone", "text", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_phone(self, value):
        normalized = normalize_phone(value)
        if not normalized:
            raise serializers.ValidationError("Enter a valid phone number.")
        return normalized
