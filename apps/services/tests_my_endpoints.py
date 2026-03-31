from django.test import SimpleTestCase


class VendorMyEndpointsAuthTests(SimpleTestCase):
    def test_services_my_requires_authentication(self):
        response = self.client.get("/api/services/my/")

        self.assertIn(response.status_code, {401, 403})

    def test_service_products_my_requires_authentication(self):
        response = self.client.get("/api/services/1/products/my/")

        self.assertIn(response.status_code, {401, 403})
