from django.test import SimpleTestCase, TestCase, override_settings
from unittest.mock import patch

from apps.categories.models import Category
from apps.regions.models import City, Region
from apps.services.models import Service
from apps.system.models import ClientFeedback
from apps.users.models import RoleEnum, User


@override_settings(
    MAP_TILE_URL="https://tiles.example.com/{z}/{x}/{y}.png",
    MAP_ATTRIBUTION="© OpenStreetMap contributors",
    MAP_MIN_ZOOM=0,
    MAP_MAX_ZOOM=19,
    MAP_CONFIG_CACHE_MAX_AGE=3600,
)
class SystemMapConfigTests(SimpleTestCase):
    def test_map_config_is_public_and_returns_expected_payload(self):
        response = self.client.get("/api/system/map-config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "tile_url": "https://tiles.example.com/{z}/{x}/{y}.png",
                "attribution": "© OpenStreetMap contributors",
                "min_zoom": 0,
                "max_zoom": 19,
            },
        )

    def test_map_config_returns_cache_headers(self):
        response = self.client.get("/api/system/map-config/")

        self.assertEqual(response.status_code, 200)
        cache_control = response.headers.get("Cache-Control", "")
        self.assertIn("max-age=3600", cache_control)
        self.assertIn("public", cache_control)


@override_settings(SUPPORT_EMAIL="support@example.com")
class SupportPageTests(TestCase):
    def test_support_page_is_public(self):
        response = self.client.get("/support/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kejebe Support")
        self.assertContains(response, "support@example.com")

    def test_support_page_creates_feedback_request(self):
        response = self.client.post(
            "/support/",
            {
                "name": "Test User",
                "phone": "61111111",
                "message": "I need help with my account.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your support request has been received")
        self.assertEqual(ClientFeedback.objects.count(), 1)

        feedback = ClientFeedback.objects.get()
        self.assertEqual(feedback.name, "Test User")
        self.assertEqual(feedback.phone, "+99361111111")
        self.assertEqual(feedback.message, "I need help with my account.")


@override_settings(
    DEEPLINK_APP_SCHEME="kejebe",
    IOS_APP_STORE_URL="https://apps.apple.com/app/kejebe/id123456789",
    ANDROID_PLAY_STORE_URL="https://play.google.com/store/apps/details?id=com.kejebe.app",
)
class ServiceDeepLinkPageTests(TestCase):
    def setUp(self):
        self.bleach_clean_patcher = patch(
            "django_summernote.fields.bleach.clean",
            side_effect=lambda value, **kwargs: value,
        )
        self.bleach_clean_patcher.start()
        self.addCleanup(self.bleach_clean_patcher.stop)

        self.region = Region.objects.create(name_tm="Ashgabat welaýaty", name_ru="Ашхабадский велаят")
        self.city = City.objects.create(region=self.region, name_tm="Aşgabat", name_ru="Ашхабад")
        self.category = Category.objects.create(name_tm="Gözellik", name_ru="Красота")
        self.vendor = User.objects.create_user(
            phone="+99361111111",
            password="testpass123",
            role=RoleEnum.VENDOR,
        )
        self.service = Service.objects.create(
            vendor=self.vendor,
            category=self.category,
            city=self.city,
            title_tm="Saç hyzmaty",
            title_ru="Услуги для волос",
            description_tm="<p>Professional hyzmat.</p>",
            description_ru="<p>Профессиональный сервис.</p>",
            price_min=100,
            price_max=250,
            is_active=True,
        )

    def test_service_deep_link_page_is_public(self):
        response = self.client.get(f"/s/{self.service.id}", HTTP_ACCEPT_LANGUAGE="ru")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Услуги для волос")
        self.assertContains(response, "kejebe://service/")
        self.assertContains(response, "App Store")
        self.assertContains(response, "Google Play")

    def test_service_deep_link_page_strips_html_from_description(self):
        self.service.description_ru = "&lt;p&gt;Описание <strong>сервиса</strong>&lt;/p&gt;"
        self.service.save(update_fields=["description_ru"])

        response = self.client.get(f"/s/{self.service.id}", HTTP_ACCEPT_LANGUAGE="ru")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Описание сервиса")
        self.assertNotContains(response, "&lt;p&gt;")
        self.assertNotContains(response, "<strong>")

    def test_service_deep_link_page_returns_fallback_page_for_inactive_service(self):
        self.service.is_active = False
        self.service.save(update_fields=["is_active"])

        response = self.client.get(f"/s/{self.service.id}")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Service not found", status_code=404)
        self.assertContains(response, "kejebe://service/", status_code=404)


@override_settings(
    IOS_ASSOCIATED_APP_IDS=["ABCDE12345.com.kejebe.app"],
    ANDROID_ASSET_LINKS=[
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.kejebe.app",
                "sha256_cert_fingerprints": [
                    "AA:BB:CC:DD:EE:FF"
                ],
            },
        }
    ],
)
class DeepLinkAssociationFileTests(SimpleTestCase):
    def test_apple_app_site_association_returns_expected_payload(self):
        response = self.client.get("/apple-app-site-association")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "applinks": {
                    "apps": [],
                    "details": [
                        {
                            "appID": "ABCDE12345.com.kejebe.app",
                            "paths": ["/s/*"],
                        }
                    ],
                }
            },
        )

    def test_android_assetlinks_returns_expected_payload(self):
        response = self.client.get("/.well-known/assetlinks.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "relation": ["delegate_permission/common.handle_all_urls"],
                    "target": {
                        "namespace": "android_app",
                        "package_name": "com.kejebe.app",
                        "sha256_cert_fingerprints": [
                            "AA:BB:CC:DD:EE:FF"
                        ],
                    },
                }
            ],
        )


@override_settings(
    TERMS_VERSION="2026-04-23",
    TERMS_LAST_UPDATED="2026-04-23T00:00:00Z",
    SUPPORT_EMAIL="support@example.com",
)
class TermsAndLegalEndpointTests(SimpleTestCase):
    def test_terms_page_is_public(self):
        response = self.client.get("/terms-of-use")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Last updated")
        self.assertContains(response, "support@example.com")
        self.assertContains(response, "/privacy-policy")

    def test_terms_page_supports_ru_and_tm_language(self):
        response_ru = self.client.get("/terms-of-use?lang=ru")
        response_tm = self.client.get("/terms-of-use?lang=tm")

        self.assertEqual(response_ru.status_code, 200)
        self.assertEqual(response_tm.status_code, 200)
        self.assertContains(response_ru, "Условия использования")
        self.assertContains(response_tm, "Ulanyş Şertleri")

    def test_legal_terms_endpoint_returns_url_and_version(self):
        response = self.client.get("/api/v1/legal/terms")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["version"], "2026-04-23")
        self.assertIn("/terms-of-use", payload["url"])
        self.assertTrue(payload["last_updated"].startswith("2026-04-23T00:00:00"))
