from django.test import SimpleTestCase, TestCase, override_settings

from apps.system.models import ClientFeedback


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
