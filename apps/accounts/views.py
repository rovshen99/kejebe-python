from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import InboundSMS, SMSChallenge
from .serializers import ConfirmChallengeSerializer, InitChallengeSerializer, InboundSMSSerializer
from .services.phone import is_bypass_number, normalize_phone
from apps.devices.models import Device

User = get_user_model()


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def get_or_create_user_from_validated(phone, validated):
    return User.objects.get_or_create(
        phone=phone,
        defaults={
            'name': validated.get('name', ''),
            'email': validated.get('email') or None,
            'role': (
                validated.get('role')
                or getattr(User, 'DEFAULT_ROLE', 'customer')
            ),
        },
    )


def build_user_payload(request, user):
    has_avatar = getattr(user, 'avatar', None) and user.avatar
    avatar_url = (
        request.build_absolute_uri(user.avatar.url) if has_avatar else None
    )

    return {
        'uuid': str(getattr(user, 'uuid', '')),
        'phone': user.phone,
        'name': getattr(user, 'name', ''),
        'email': getattr(user, 'email', None),
        'role': getattr(user, 'role', None),
        'avatar': avatar_url,
    }


@extend_schema(
    tags=['SMS'],
    summary='Inbound SMS webhook',
    description=(
        'Accepts inbound SMS (generic: From/To/Body/MessageSid) '
        'or client payload (sender/message/receivedInMilli).'
    ),
    request=InboundSMSSerializer,
)
class InboundSMSWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        api_key = request.headers.get("X-API-KEY") or request.headers.get("x-api-key")
        expected = getattr(settings, "SMS_INBOUND_API_KEY", "")
        if expected:
            if not api_key or api_key != expected:
                return Response({"detail": "invalid_api_key"}, status=403)
        data = request.data
        received_at = self._parse_received_at(data)
        from_number = normalize_phone(
            data.get('From') or data.get('from') or data.get('sender') or ''
        )
        to_number = normalize_phone(
            data.get('To') or data.get('to') or data.get('receiver') or settings.SMS_SERVICE_NUMBER
        )
        body = data.get('Body') or data.get('body') or data.get('message') or ''
        msg_id = data.get('MessageSid') or data.get('message_id') or ''
        if not from_number or not to_number:
            return Response({'detail': 'Missing numbers'}, status=400)
        InboundSMS.objects.create(
            provider='generic',
            provider_message_id=msg_id,
            from_number=from_number,
            to_number=to_number,
            body=body,
            received_at=received_at,
        )
        return Response(status=201)

    @staticmethod
    def _parse_received_at(data):
        raw = data.get("receivedInMilli") or data.get("received_in_milli") or data.get("received_at")
        if raw in (None, ""):
            return timezone.now()
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return timezone.now()
        if value > 1_000_000_000_000:
            value = value / 1000
        tz = timezone.get_current_timezone()
        return datetime.fromtimestamp(value, tz=tz)


@extend_schema(
    request=InitChallengeSerializer,
    responses={
        201: {
            'type': 'object',
            'properties': {
                'challenge_id': {
                    'type': 'string',
                    'format': 'uuid',
                },
                'expires_at': {
                    'type': 'string',
                    'format': 'date-time',
                },
            },
        }
    },
    tags=['Auth'],
    summary='Start reverse-SMS verification',
    description=(
        'Initiates a reverse-SMS verification challenge and returns '
        'its ID and expiry.'
    ),
)
class InitReverseSMSView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = InitChallengeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from_number = normalize_phone(serializer.validated_data['phone'])
        to_number = normalize_phone(getattr(settings, 'SMS_SERVICE_NUMBER', ''))
        challenge = SMSChallenge.create(
            from_number,
            to_number,
            serializer.validated_data['ttl_seconds'],
        )
        return Response(
            {
                'challenge_id': str(challenge.id),
                'expires_at': challenge.expires_at,
                'phone_number': settings.SMS_SERVICE_NUMBER,
            },
            status=201,
        )


@extend_schema(
    request=ConfirmChallengeSerializer,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'verified': {'type': 'boolean'},
                'user': {'type': 'object'},
                'tokens': {'type': 'object'},
            },
        }
    },
    tags=['Auth'],
    summary='Confirm reverse-SMS and login/register',
    description=(
        'Checks the challenge result; on success, logs in or creates a '
        'user and returns tokens.'
    ),
)
class ConfirmReverseSMSView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ConfirmChallengeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cid = serializer.validated_data['challenge_id']
        try:
            ch = SMSChallenge.objects.get(pk=cid)
        except SMSChallenge.DoesNotExist:
            return Response(
                {'verified': False, 'detail': 'invalid_challenge'},
                status=200,
            )

        if is_bypass_number(ch.from_number):
            if not ch.is_verified:
                ch.verified_at = timezone.now()
                ch.save(update_fields=['verified_at'])

        if ch.is_expired:
            return Response({'verified': False, 'detail': 'expired'}, status=200)

        if not ch.is_verified:
            found = InboundSMS.objects.filter(
                from_number=ch.from_number,
                to_number=ch.to_number,
                received_at__gte=ch.created_at
            ).exists()
            if found:
                ch.verified_at = timezone.now()
                ch.save(update_fields=['verified_at'])

        if not ch.is_verified:
            return Response({'verified': False}, status=200)

        phone = ch.from_number
        user, created = get_or_create_user_from_validated(
            phone, serializer.validated_data
        )
        self._bind_device(request, user)
        tokens = issue_tokens(user)
        payload = build_user_payload(request, user)
        return Response(
            {
                'verified': True,
                'created': created,
                'user': payload,
                'tokens': tokens,
            },
            status=200,
        )

    def _bind_device(self, request, user):
        device_id = (
            request.headers.get("X-Device-ID")
            or request.headers.get("X-Device-Id")
            or request.query_params.get("device_id")
        )
        platform = (
            request.headers.get("X-Platform")
            or request.query_params.get("platform")
            or Device.Platform.UNKNOWN
        )
        if not device_id:
            return

        device, created = Device.objects.get_or_create(
            device_id=device_id,
            defaults={"platform": platform, "user": user},
        )
        if not created and device.user_id != user.id:
            device.user = user
            device.save(update_fields=["user", "updated_at"])
