from django.test import TestCase, override_settings


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
class CategoriesCorsTests(TestCase):
    def test_categories_get_returns_cors_headers_for_allowed_origin(self):
        response = self.client.get(
            "/api/v1/categories/",
            HTTP_ORIGIN="http://localhost:5173",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "http://localhost:5173",
        )
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Credentials"),
            "true",
        )

    def test_categories_options_preflight_returns_cors_headers(self):
        response = self.client.options(
            "/api/v1/categories/",
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "http://localhost:5173",
        )
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Headers"),
            "authorization,content-type",
        )
