from django.test import SimpleTestCase


class VendorMyEndpointsAuthTests(SimpleTestCase):
    def test_services_my_requires_authentication(self):
        response = self.client.get("/api/services/my/")

        self.assertIn(response.status_code, {401, 403})

    def test_service_products_my_requires_authentication(self):
        response = self.client.get("/api/services/1/products/my/")

        self.assertIn(response.status_code, {401, 403})

    def test_vendor_me_requires_authentication(self):
        response = self.client.get("/api/v1/vendor/me/")

        self.assertIn(response.status_code, {401, 403})

    def test_vendor_services_requires_authentication(self):
        response = self.client.get("/api/v1/vendor/services/")

        self.assertIn(response.status_code, {401, 403})

    def test_vendor_products_requires_authentication(self):
        response = self.client.get("/api/v1/vendor/services/1/products/")

        self.assertIn(response.status_code, {401, 403})

    def test_vendor_contacts_requires_authentication(self):
        response = self.client.get("/api/v1/vendor/services/1/contacts/")

        self.assertIn(response.status_code, {401, 403})
