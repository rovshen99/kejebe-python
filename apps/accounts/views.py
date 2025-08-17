from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from .models import InboundSMS, SMSChallenge
from .serializers import InitChallengeSerializer, ConfirmChallengeSerializer
from .services.phone import normalize_phone, is_bypass_number

User = get_user_model()


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


@extend_schema(
    tags=["SMS"], summary="Вебхук входящих SMS",
    description="Принимает SMS от провайдера (универсально: From/To/Body/MessageSid).",
)
class InboundSMSWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data
        from_number = normalize_phone(data.get('From') or data.get('from') or '')
        to_number   = normalize_phone(data.get('To')   or data.get('to')   or settings.SMS_SERVICE_NUMBER)
        body = data.get('Body') or data.get('body') or ''
        msg_id = data.get('MessageSid') or data.get('message_id') or ''
        if not from_number or not to_number:
            return Response({"detail": "Missing numbers"}, status=400)
        InboundSMS.objects.create(
            provider="generic",
            provider_message_id=msg_id,
            from_number=from_number,
            to_number=to_number,
            body=body,
            received_at=timezone.now(),
        )
        return Response(status=201)


@extend_schema(
    request=InitChallengeSerializer,
    responses={201: {"type":"object","properties":{"challenge_id":{"type":"string","format":"uuid"},"expires_at":{"type":"string","format":"date-time"}}}},
    tags=["Auth"], summary="Старт реверс-SMS проверки"
)
class InitReverseSMSView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = InitChallengeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        from_number = normalize_phone(s.validated_data["phone"])
        to_number = normalize_phone(getattr(settings, "SMS_SERVICE_NUMBER", ""))
        ch = SMSChallenge.create(from_number, to_number, s.validated_data["ttl_seconds"])
        return Response({"challenge_id": str(ch.id), "expires_at": ch.expires_at}, status=201)


@extend_schema(
    request=ConfirmChallengeSerializer,
    responses={200: {"type":"object","properties":{
        "verified":{"type":"boolean"},
        "user":{"type":"object"},
        "tokens":{"type":"object"}
    }}},
    tags=["Auth"], summary="Подтверждение реверс-SMS и логин/регистрация"
)
class ConfirmReverseSMSView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = ConfirmChallengeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        cid = s.validated_data["challenge_id"]
        try:
            ch = SMSChallenge.objects.get(pk=cid)
        except SMSChallenge.DoesNotExist:
            return Response({"verified": False, "detail": "invalid_challenge"}, status=200)

        if is_bypass_number(ch.from_number):
            if not ch.is_verified:
                ch.verified_at = timezone.now()
                ch.save(update_fields=["verified_at"])
            phone = ch.from_number
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    "name": s.validated_data.get("name", ""),
                    "email": s.validated_data.get("email") or None,
                    "role": s.validated_data.get("role") or getattr(User, "DEFAULT_ROLE", "customer"),
                }
            )
            tokens = issue_tokens(user)
            payload = {"uuid": str(getattr(user, "uuid", "")), "phone": user.phone, "name": getattr(user, "name", ""),
                       "email": getattr(user, "email", None), "role": getattr(user, "role", None)}
            return Response({"verified": True, "user": payload, "tokens": tokens}, status=200)

        if ch.is_expired:
            return Response({"verified": False, "detail": "expired"}, status=200)

        if not ch.is_verified:
            found = InboundSMS.objects.filter(
                from_number=ch.from_number,
                to_number=ch.to_number,
                received_at__gte=ch.created_at
            ).exists()
            if found:
                ch.verified_at = timezone.now()
                ch.save(update_fields=["verified_at"])

        if not ch.is_verified:
            return Response({"verified": False}, status=200)

        phone = ch.from_number
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                "name": s.validated_data.get("name", ""),
                "email": s.validated_data.get("email") or None,
                "role": s.validated_data.get("role") or getattr(User, "DEFAULT_ROLE", "customer"),
            }
        )

        tokens = issue_tokens(user)

        user_payload = {"uuid": str(getattr(user, "uuid", "")), "phone": user.phone, "name": getattr(user, "name", ""), "email": getattr(user, "email", None), "role": getattr(user, "role", None)}
        return Response({"verified": True, "user": user_payload, "tokens": tokens}, status=200)
