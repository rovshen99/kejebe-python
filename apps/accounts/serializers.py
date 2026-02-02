from rest_framework import serializers


class InitChallengeSerializer(serializers.Serializer):
    phone = serializers.CharField()
    ttl_seconds = serializers.IntegerField(required=False, min_value=60, max_value=1800, default=600)


class ConfirmChallengeSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    role = serializers.CharField(required=False)


class InboundSMSSerializer(serializers.Serializer):
    From = serializers.CharField(required=False, allow_blank=True)
    To = serializers.CharField(required=False, allow_blank=True)
    Body = serializers.CharField(required=False, allow_blank=True)
    MessageSid = serializers.CharField(required=False, allow_blank=True)
    from_ = serializers.CharField(source='from', required=False, allow_blank=True)
    to = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True)
    message_id = serializers.CharField(required=False, allow_blank=True)
    sender = serializers.CharField(required=False, allow_blank=True)
    receiver = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    receivedInMilli = serializers.IntegerField(required=False)
    received_in_milli = serializers.IntegerField(required=False)
    received_at = serializers.DateTimeField(required=False)
