from django.test import SimpleTestCase, override_settings


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
