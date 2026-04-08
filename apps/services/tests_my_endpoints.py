from django.test import SimpleTestCase

from apps.services.vendor_serializers import VendorServiceProductWriteSerializer


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


class VendorProductSerializerContractTests(SimpleTestCase):
    def test_product_write_serializer_accepts_images(self):
        serializer = VendorServiceProductWriteSerializer()

        self.assertIn("images", serializer.fields)
        self.assertTrue(serializer.fields["images"].write_only)
