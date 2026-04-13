from drf_spectacular.utils import extend_schema
from django.shortcuts import render
from django.conf import settings
from django.utils.cache import patch_cache_control, patch_response_headers
from rest_framework import mixins, permissions, viewsets, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SystemContact, AccountDeletionRequest, SystemAbout, ClientFeedback
from .serializers import SystemContactSerializer, SystemAboutSerializer, ClientFeedbackSerializer, MapConfigSerializer
from .forms import DeleteAccountForm, SupportRequestForm
from .throttles import FeedbackIPThrottle


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


def delete_account_view(request):
    success = False
    if request.method == "POST":
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            AccountDeletionRequest.objects.create(phone=form.cleaned_data["phone"])
            success = True
            form = DeleteAccountForm()
    else:
        form = DeleteAccountForm()

    return render(
        request,
        "delete_account.html",
        {
            "form": form,
            "success": success,
            "app_name": "Kejebe",
            "developer_name": "Rovshen Berdimyradov",
            "support_email": getattr(settings, "SUPPORT_EMAIL", "berdimuradowr@gmail.com"),
        },
    )


def support_view(request):
    success = False
    if request.method == "POST":
        form = SupportRequestForm(request.POST)
        if form.is_valid():
            ClientFeedback.objects.create(
                name=form.cleaned_data["name"],
                phone=form.cleaned_data["phone"],
                message=form.cleaned_data["message"],
            )
            success = True
            form = SupportRequestForm()
    else:
        form = SupportRequestForm()

    return render(
        request,
        "support.html",
        {
            "form": form,
            "success": success,
            "app_name": "Kejebe",
            "developer_name": "Rovshen Berdimyradov",
            "support_email": getattr(settings, "SUPPORT_EMAIL", "berdimuradowr@gmail.com"),
        },
    )


class SystemAboutView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(tags=["System"], responses=SystemAboutSerializer)
    def get(self, request):
        about = SystemAbout.objects.order_by("-updated_at", "-id").first()
        if not about:
            return Response({"about_tm": "", "about_ru": ""})
        return Response(SystemAboutSerializer(about).data)


class SystemMapConfigView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(tags=["System"], responses=MapConfigSerializer)
    def get(self, request):
        payload = {
            "tile_url": getattr(settings, "MAP_TILE_URL", "") or getattr(settings, "OSM_TILE_URL", ""),
            "attribution": getattr(settings, "MAP_ATTRIBUTION", "© OpenStreetMap contributors"),
            "min_zoom": getattr(settings, "MAP_MIN_ZOOM", 0),
            "max_zoom": getattr(settings, "MAP_MAX_ZOOM", 19),
        }
        response = Response(MapConfigSerializer(payload).data)
        cache_timeout = max(int(getattr(settings, "MAP_CONFIG_CACHE_MAX_AGE", 3600)), 0)
        patch_response_headers(response, cache_timeout=cache_timeout)
        patch_cache_control(response, public=True, max_age=cache_timeout)
        return response


@extend_schema(
    tags=["System"],
    request=ClientFeedbackSerializer,
    responses={201: ClientFeedbackSerializer, 429: None},
)
class ClientFeedbackCreateView(generics.CreateAPIView):
    queryset = ClientFeedback.objects.all()
    serializer_class = ClientFeedbackSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [FeedbackIPThrottle]
