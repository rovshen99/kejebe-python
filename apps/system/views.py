from drf_spectacular.utils import extend_schema
from html import unescape
from datetime import datetime, timezone
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_response_headers
from django.utils.dateparse import parse_datetime
from django.utils.html import strip_tags
from django.utils.text import Truncator
from rest_framework import mixins, permissions, viewsets, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.services.models import Service
from .models import SystemContact, AccountDeletionRequest, SystemAbout, ClientFeedback
from .serializers import (
    SystemContactSerializer,
    SystemAboutSerializer,
    ClientFeedbackSerializer,
    MapConfigSerializer,
    TermsInfoSerializer,
)
from .forms import DeleteAccountForm, SupportRequestForm
from .throttles import FeedbackIPThrottle
from core.utils import format_price_text, get_lang_code, localized_value


LEGAL_TEXTS = {
    "en": {
        "title": "Terms of Use",
        "last_updated_label": "Last updated",
        "privacy_policy_label": "Privacy Policy",
        "report_email": "Support and appeals",
        "content": [
            "By using Kejebe, you agree not to post, upload, or share objectionable, abusive, hateful, illegal, sexually explicit, violent, fraudulent, or otherwise harmful content.",
            "Users must behave respectfully. Harassment, threats, scams, impersonation, and repeated abusive behavior are prohibited.",
            "Kejebe moderators may remove content, restrict features, suspend, or permanently ban accounts that violate these Terms.",
            "If you see violating content, use the in-app report flow (for example, report a review) or contact support.",
            "All reports are reviewed within 24 hours. Repeated or severe violations can result in content removal and user ejection/ban.",
            "If your content or account is moderated, you may submit an appeal via support email.",
            "You are responsible for content you publish and for compliance with applicable law in your jurisdiction.",
            "Your use of Kejebe is also governed by our Privacy Policy.",
        ],
    },
    "ru": {
        "title": "Условия использования",
        "last_updated_label": "Последнее обновление",
        "privacy_policy_label": "Политика конфиденциальности",
        "report_email": "Поддержка и апелляции",
        "content": [
            "Используя Kejebe, вы обязуетесь не публиковать недопустимый, оскорбительный, незаконный, экстремистский, сексуально-явный, насильственный, мошеннический или иной вредоносный контент.",
            "Пользователь обязан соблюдать уважительное поведение. Запрещены травля, угрозы, обман, выдача себя за другого и повторяющееся агрессивное поведение.",
            "Модераторы Kejebe вправе удалять контент, ограничивать функции, временно блокировать или полностью блокировать аккаунты за нарушения.",
            "Если вы обнаружили нарушение, используйте in-app flow жалобы (например, жалоба на отзыв) или свяжитесь с поддержкой.",
            "Все жалобы рассматриваются в течение 24 часов. Повторные и тяжёлые нарушения приводят к удалению контента и блокировке пользователя.",
            "Если ваш контент или аккаунт был ограничен, вы можете подать апелляцию через email поддержки.",
            "Вы несёте ответственность за публикуемый контент и соблюдение применимого законодательства вашей юрисдикции.",
            "Использование Kejebe также регулируется нашей Политикой конфиденциальности.",
        ],
    },
    "tm": {
        "title": "Ulanyş Şertleri",
        "last_updated_label": "Soňky täzelenme",
        "privacy_policy_label": "Gizlinlik Syýasaty",
        "report_email": "Goldaw we şikaýat/appeal",
        "content": [
            "Kejebe ulanan wagtyňyzda, garşylykly, gödek, bikanun, ýigrenç döredýän, aç-açan seksual, zorlukly, galplyk ýa-da zyýanly kontent ýerleşdirmek gadagan.",
            "Ulanyjylar hormat bilen gatnaşmaly. Gorkuzma, haýbat, aldaw, başga adamyň ornuna çykyş etmek we gaýtalanýan gödek hereketler gadagan.",
            "Kejebe moderatorlary bu şertler bozulsa, kontenti aýyrmaga, mümkinçilikleri çäklendirmäge, wagtlaýyn ýa-da hemişelik bloklamaga haklydyr.",
            "Eger bozulan kontent görseňiz, programmanyň içindäki report flow ulanyň (mysal: review report) ýa-da goldaw bilen habarlaşyň.",
            "Ähli reportlar 24 sagadyň dowamynda gözden geçirilýär. Gaýtalanýan ýa-da agyr bozmalarda kontent aýrylýar we ulanyjy ban edilýär.",
            "Kontentiňiz ýa-da akkauntyňyz boýunça çäre görülen bolsa, goldaw email arkaly appeal iberip bilersiňiz.",
            "Siz öz ýerleşdirýän kontentiňiz we öz ýurisdiksiýaňyzdaky kanunlara laýyklyk üçin jogapkärsiňiz.",
            "Kejebe ulanylyşy Gizlinlik Syýasaty bilen hem düzgünleşdirilýär.",
        ],
    },
}

PRIVACY_TEXTS = {
    "en": {
        "title": "Privacy Policy",
        "last_updated_label": "Last updated",
        "intro": [
            "This Privacy Policy describes Our policies and procedures on the collection, use and disclosure of Your information when You use the Service and tells You about Your privacy rights and how the law protects You.",
            "We use Your Personal Data to provide and improve the Service. By using the Service, You agree to the collection and use of information in accordance with this Privacy Policy.",
        ],
        "sections": [
            {
                "heading": "Interpretation and Definitions",
                "items": [
                    "The words whose initial letters are capitalized have meanings defined under the following conditions.",
                    "Account means a unique account created for You to access our Service or parts of our Service.",
                    "Application refers to Kejebe, the software program provided by the Company.",
                    "Company (referred to as either \"the Company\", \"We\", \"Us\" or \"Our\") refers to Kejebe.",
                    "Country refers to: Turkmenistan.",
                    "Device means any device that can access the Service such as a computer, a cell phone or a digital tablet.",
                    "Personal Data is any information that relates to an identified or identifiable individual.",
                    "Service refers to the Application.",
                    "Service Provider means any natural or legal person who processes the data on behalf of the Company.",
                    "Usage Data refers to data collected automatically from the use of the Service.",
                ],
            },
            {
                "heading": "Collecting and Using Your Personal Data",
                "items": [
                    "While using Our Service, We may ask You to provide personally identifiable information, including email address, first and last name, phone number, address and Usage Data.",
                    "Usage Data may include IP address, browser type/version, visited pages, time and date of visit, time spent, unique device identifiers and diagnostic data.",
                    "When You use a mobile device, We may collect device type, unique mobile ID, mobile OS, IP address and similar technical data.",
                    "While using the Application, and with Your prior permission, We may collect pictures and other information from Your Device camera and photo library.",
                ],
            },
            {
                "heading": "Use of Your Personal Data",
                "items": [
                    "To provide and maintain the Service.",
                    "To manage Your Account and Your registration.",
                    "For performance of a contract and support of requested services.",
                    "To contact You via email, phone, SMS, or similar communications.",
                    "To provide news, offers and product/service updates (unless You opt out).",
                    "For business transfers and reorganization scenarios.",
                    "For analytics, improvement, security and fraud prevention.",
                ],
            },
            {
                "heading": "Sharing of Your Personal Data",
                "items": [
                    "With Service Providers to operate, analyze and support the Service.",
                    "For business transfers such as merger, acquisition or asset sale.",
                    "With Affiliates and business partners under applicable obligations.",
                    "With other users when You post in public areas.",
                    "With Your consent for other purposes.",
                ],
            },
            {
                "heading": "Retention, Transfer and Deletion",
                "items": [
                    "We retain Personal Data only as long as necessary for purposes in this Policy and legal obligations.",
                    "Usage Data is generally retained for shorter periods unless needed for security or legal reasons.",
                    "Your data may be transferred to and processed in jurisdictions outside Your location.",
                    "You may request deletion, correction or access to Your Personal Data.",
                    "We may retain some information where legally required.",
                ],
            },
            {
                "heading": "Disclosure and Security",
                "items": [
                    "We may disclose data for legal obligations, law enforcement, and protection of rights, users and public safety.",
                    "No internet transmission or storage method is 100% secure, but We apply reasonable safeguards.",
                ],
            },
            {
                "heading": "Children's Privacy",
                "items": [
                    "Our Service does not address anyone under 13.",
                    "If We learn We collected Personal Data from a child without required consent, We will take steps to remove such information.",
                ],
            },
            {
                "heading": "Third-Party Links and Changes",
                "items": [
                    "Our Service may contain links to third-party sites. We are not responsible for their privacy practices.",
                    "We may update this Privacy Policy from time to time and will update the Last updated date.",
                ],
            },
        ],
        "contact_label": "Contact Us",
        "contact_hint": "If You have any questions about this Privacy Policy, You can contact us by email:",
    },
    "ru": {
        "title": "Политика конфиденциальности",
        "last_updated_label": "Последнее обновление",
        "intro": [
            "Эта Политика конфиденциальности описывает, как Kejebe собирает, использует и раскрывает ваши данные при использовании сервиса.",
            "Используя сервис, вы соглашаетесь с обработкой персональных данных в соответствии с этой Политикой.",
        ],
        "sections": [
            {
                "heading": "Какие данные мы собираем",
                "items": [
                    "Данные аккаунта: имя, email, телефон и иные данные, которые вы указываете.",
                    "Технические данные: IP, устройство, ОС, идентификаторы и диагностические события.",
                    "Медиа-данные: фото и контент, который вы загружаете с разрешения устройства.",
                ],
            },
            {
                "heading": "Как мы используем данные",
                "items": [
                    "Для предоставления и улучшения сервиса.",
                    "Для модерации, безопасности и обработки жалоб.",
                    "Для связи с вами по вопросам аккаунта и работы сервиса.",
                ],
            },
            {
                "heading": "Передача, хранение и удаление",
                "items": [
                    "Мы храним данные только столько, сколько необходимо для целей сервиса и закона.",
                    "Вы можете запросить доступ, исправление или удаление персональных данных.",
                    "Некоторые данные могут храниться дольше при наличии юридической обязанности.",
                ],
            },
            {
                "heading": "Ссылки и обновления",
                "items": [
                    "Мы не отвечаем за политику сторонних сайтов по внешним ссылкам.",
                    "Политика может обновляться; актуальная версия публикуется на этой странице.",
                ],
            },
        ],
        "contact_label": "Связаться с нами",
        "contact_hint": "Если у вас есть вопросы по Политике конфиденциальности, напишите нам:",
    },
    "tm": {
        "title": "Gizlinlik Syýasaty",
        "last_updated_label": "Soňky täzelenme",
        "intro": [
            "Bu Gizlinlik Syýasaty Kejebe tarapyndan maglumatlaryň nähili ýygnalýandygyny, ulanylýandygyny we paýlaşylýandygyny düşündirýär.",
            "Servisi ulanmak bilen, siz bu syýasata laýyklykda maglumat işlenmegine razy bolýarsyňyz.",
        ],
        "sections": [
            {
                "heading": "Ýygnalýan maglumatlar",
                "items": [
                    "Akkaunt maglumatlary: adyňyz, email, telefon we girizen beýleki maglumatlar.",
                    "Tehniki maglumatlar: IP, enjam, OS, enjam ID-lary we diagnostika maglumatlary.",
                    "Media maglumatlar: enjam rugsady bilen ýüklän suratlaryňyz we kontentiňiz.",
                ],
            },
            {
                "heading": "Maglumatlaryň ulanylyşy",
                "items": [
                    "Servisi hödürlemek we gowulandyrmak üçin.",
                    "Moderasiýa, howpsuzlyk we report işlemleri üçin.",
                    "Akkaunt we hyzmat boýunça sizi habarly etmek üçin.",
                ],
            },
            {
                "heading": "Saklamak, geçirmek we pozmak",
                "items": [
                    "Maglumatlar diňe zerur möhletde saklanýar.",
                    "Siz öz maglumatlaryňyza elýeterlilik, düzediş ýa-da pozmak talap edip bilersiňiz.",
                    "Kanuny esaslar bolanda käbir maglumatlar uzak saklanyp bilner.",
                ],
            },
            {
                "heading": "Täzelenmeler",
                "items": [
                    "Daşarky sahypalaryň gizlinlik syýasaty üçin jogapkärçilik çekmeýäris.",
                    "Syýasat täzelenip bilner, iň soňky görnüşi şu sahypada ýerleşdirilýär.",
                ],
            },
        ],
        "contact_label": "Biziň bilen habarlaşyň",
        "contact_hint": "Gizlinlik Syýasaty barada soragyňyz bolsa, email arkaly habarlaşyň:",
    },
}


def _resolve_legal_lang(request) -> str:
    qp_lang = request.GET.get("lang", "") if hasattr(request, "GET") else ""
    qp_short = qp_lang.split("-")[0].lower() if qp_lang else ""
    if qp_short in LEGAL_TEXTS:
        return qp_short
    lang = get_lang_code(request=request, supported=("ru", "en", "tm"), default="en")
    return lang if lang in LEGAL_TEXTS else "en"


def _parse_terms_last_updated():
    raw = getattr(settings, "TERMS_LAST_UPDATED", "2026-04-23T00:00:00Z")
    parsed = parse_datetime(raw)
    if parsed is not None:
        return parsed
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        dt = datetime(2026, 4, 23, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _terms_url(request) -> str:
    return request.build_absolute_uri(reverse("terms-of-use"))


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


def terms_of_use_view(request):
    lang = _resolve_legal_lang(request)
    text = LEGAL_TEXTS[lang]
    return render(
        request,
        "terms_of_use.html",
        {
            "lang": lang,
            "title": text["title"],
            "terms_items": text["content"],
            "last_updated_label": text["last_updated_label"],
            "last_updated": getattr(settings, "TERMS_VERSION", "2026-04-23"),
            "privacy_policy_label": text["privacy_policy_label"],
            "report_email_label": text["report_email"],
            "support_email": getattr(settings, "SUPPORT_EMAIL", "support@example.com"),
            "privacy_url": reverse("privacy-policy"),
        },
    )


def privacy_policy_view(request):
    lang = _resolve_legal_lang(request)
    text = PRIVACY_TEXTS[lang]
    return render(
        request,
        "privacy_policy.html",
        {
            "lang": lang,
            "title": text["title"],
            "intro": text["intro"],
            "sections": text["sections"],
            "last_updated_label": text["last_updated_label"],
            "contact_label": text["contact_label"],
            "contact_hint": text["contact_hint"],
            "last_updated": getattr(settings, "TERMS_VERSION", "2026-04-23"),
            "support_email": getattr(settings, "SUPPORT_EMAIL", "support@example.com"),
        },
    )


class TermsInfoView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(tags=["System"], responses=TermsInfoSerializer)
    def get(self, request):
        payload = {
            "url": _terms_url(request),
            "version": getattr(settings, "TERMS_VERSION", "2026-04-23"),
            "last_updated": _parse_terms_last_updated(),
        }
        return Response(TermsInfoSerializer(payload).data)


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
    description = Truncator(strip_tags(unescape(raw_description))).chars(200)
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
