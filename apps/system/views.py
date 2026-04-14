from drf_spectacular.utils import extend_schema
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.utils.cache import patch_cache_control, patch_response_headers
from django.utils.html import strip_tags
from django.utils.text import Truncator
from rest_framework import mixins, permissions, viewsets, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.services.models import Service
from .models import SystemContact, AccountDeletionRequest, SystemAbout, ClientFeedback
from .serializers import SystemContactSerializer, SystemAboutSerializer, ClientFeedbackSerializer, MapConfigSerializer
from .forms import DeleteAccountForm, SupportRequestForm
from .throttles import FeedbackIPThrottle
from core.utils import format_price_text, get_lang_code, localized_value


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


def service_deep_link_view(request, service_id: int):
    app_scheme = getattr(settings, "DEEPLINK_APP_SCHEME", "kejebe").strip() or "kejebe"
    app_link = f"{app_scheme}://service/{service_id}"
    common_context = {
        "app_name": "Kejebe",
        "service_id": service_id,
        "service_url": request.build_absolute_uri(),
        "app_link": app_link,
        "ios_app_store_url": getattr(settings, "IOS_APP_STORE_URL", ""),
        "android_play_store_url": getattr(settings, "ANDROID_PLAY_STORE_URL", ""),
    }
    try:
        service = (
            Service.objects.filter(is_active=True)
            .select_related("city", "city__region", "category")
            .prefetch_related("serviceimage_set")
            .get(pk=service_id)
        )
    except Service.DoesNotExist:
        response = render(
            request,
            "service_deep_link_not_found.html",
            {
                **common_context,
                "title": "Service not found",
            },
            status=404,
        )
        return response

    lang = get_lang_code(request=request, default="tm")
    title = localized_value(service, "title", lang=lang) or service.title_tm
    raw_description = localized_value(service, "description", lang=lang) or ""
    description = Truncator(strip_tags(raw_description)).chars(200)
    price_text = format_price_text(service.price_min, service.price_max, lang=lang)
    city_title = localized_value(getattr(service, "city", None), "name", lang=lang)
    category_title = localized_value(getattr(service, "category", None), "name", lang=lang)

    image_url = None
    if getattr(service, "avatar", None) and getattr(service.avatar, "url", None):
        image_url = service.avatar.url
    elif getattr(service, "background", None) and getattr(service.background, "url", None):
        image_url = service.background.url
    else:
        first_image = next(iter(service.serviceimage_set.all()), None)
        if first_image and getattr(first_image, "image", None) and getattr(first_image.image, "url", None):
            image_url = first_image.image.url

    context = {
        **common_context,
        "service": service,
        "service_id": service.id,
        "title": title,
        "description": description,
        "price_text": price_text,
        "city_title": city_title,
        "category_title": category_title,
        "image_url": image_url,
    }
    return render(request, "service_deep_link.html", context)


def apple_app_site_association_view(request):
    app_ids = getattr(settings, "IOS_ASSOCIATED_APP_IDS", [])
    if not app_ids:
        raise Http404("AASA is not configured.")

    payload = {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appID": app_id,
                    "paths": ["/s/*"],
                }
                for app_id in app_ids
            ],
        }
    }
    response = JsonResponse(payload)
    response["Content-Type"] = "application/json"
    patch_cache_control(response, public=True, max_age=3600)
    return response


def android_asset_links_view(request):
    asset_links = getattr(settings, "ANDROID_ASSET_LINKS", [])
    if not asset_links:
        raise Http404("Asset links are not configured.")

    response = JsonResponse(asset_links, safe=False)
    patch_cache_control(response, public=True, max_age=3600)
    return response
