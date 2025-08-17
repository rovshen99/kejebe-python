from rest_framework import serializers


class InitChallengeSerializer(serializers.Serializer):
    phone = serializers.CharField()
    ttl_seconds = serializers.IntegerField(required=False, min_value=60, max_value=1800, default=600)


class ConfirmChallengeSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    role = serializers.CharField(required=False)
