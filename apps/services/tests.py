from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase
from rest_framework import serializers

from core.utils import format_price_text
from apps.services.serializers import (
    ServiceApplicationSerializer,
    ServiceBaseSerializer,
    ServiceShowcaseSerializer,
    ServiceUpdateSerializer,
)
from apps.services.throttles import ServiceApplicationIPThrottle


class FormatPriceTextTests(SimpleTestCase):
    def test_price_on_request_respects_russian_language(self):
        self.assertEqual(format_price_text(None, None, lang="ru"), "Цена по запросу")

    def test_price_on_request_respects_turkmen_language(self):
        self.assertEqual(format_price_text(None, None, lang="tm"), "Bahasy soralanda")


class ServiceApplicationSerializerTests(SimpleTestCase):
    @patch("apps.services.serializers.timezone.now")
    @patch("apps.services.serializers.ServiceApplication.objects.filter")
    def test_validate_phone_normalizes_and_allows_unique_recent_phone(self, filter_mock, now_mock):
        queryset = Mock()
        queryset.exists.return_value = False
        filter_mock.return_value = queryset
        now_mock.return_value = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)

        serializer = ServiceApplicationSerializer()

        self.assertEqual(serializer.validate_phone("61 23 45 67"), "+99361234567")
        filter_mock.assert_called_once_with(
            phone="+99361234567",
            created_at__gte=datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc) - timedelta(hours=12),
        )

    @patch("apps.services.serializers.timezone.now")
    @patch("apps.services.serializers.ServiceApplication.objects.filter")
    def test_validate_phone_rejects_recent_duplicate_phone(self, filter_mock, now_mock):
        queryset = Mock()
        queryset.exists.return_value = True
        filter_mock.return_value = queryset
        now_mock.return_value = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)

        serializer = ServiceApplicationSerializer()

        with self.assertRaisesMessage(
            serializers.ValidationError,
            "An application with this phone number was already submitted in the last 12 hours.",
        ):
            serializer.validate_phone("+99361234567")

    @patch("apps.services.serializers.ServiceApplication.objects.filter")
    def test_validate_phone_rejects_non_turkmen_number(self, filter_mock):
        serializer = ServiceApplicationSerializer()

        with self.assertRaisesMessage(
            serializers.ValidationError,
            "Only Turkmen phone numbers are allowed.",
        ):
            serializer.validate_phone("+79161234567")

        filter_mock.assert_not_called()

    def test_links_reject_more_than_five_items(self):
        serializer = ServiceApplicationSerializer()

        with self.assertRaisesMessage(
            serializers.ValidationError,
            "No more than 5 links are allowed.",
        ):
            serializer.fields["links"].run_validation(
                [
                    "https://example.com/1",
                    "https://example.com/2",
                    "https://example.com/3",
                    "https://example.com/4",
                    "https://example.com/5",
                    "https://example.com/6",
                ]
            )


class ServiceApplicationIPThrottleTests(SimpleTestCase):
    def test_post_request_uses_ip_based_throttle_key(self):
        request = RequestFactory().post("/api/v1/service-applications/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        throttle = ServiceApplicationIPThrottle()

        self.assertEqual(
            throttle.get_cache_key(request, view=None),
            "throttle_service_application_ip_127.0.0.1",
        )

    def test_non_post_request_has_no_throttle_key(self):
        request = RequestFactory().get("/api/v1/service-applications/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        throttle = ServiceApplicationIPThrottle()

        self.assertIsNone(throttle.get_cache_key(request, view=None))


class ServiceSerializerFieldTests(SimpleTestCase):
    def test_service_showcase_serializer_excludes_products(self):
        self.assertNotIn("products", ServiceShowcaseSerializer.Meta.fields)

    def test_service_showcase_serializer_excludes_videos(self):
        self.assertNotIn("videos", ServiceShowcaseSerializer.Meta.fields)

    def test_service_base_serializer_includes_work_experience_years(self):
        self.assertIn("work_experience_years", ServiceBaseSerializer.Meta.fields)

    def test_service_update_serializer_includes_work_experience_years(self):
        self.assertIn("work_experience_years", ServiceUpdateSerializer.Meta.fields)

    def test_service_application_serializer_includes_work_experience_years(self):
        self.assertIn("work_experience_years", ServiceApplicationSerializer.Meta.fields)

    def test_service_application_serializer_includes_address_and_price_from(self):
        self.assertIn("address", ServiceApplicationSerializer.Meta.fields)
        self.assertIn("price_from", ServiceApplicationSerializer.Meta.fields)

    def test_service_application_serializer_includes_links(self):
        self.assertIn("links", ServiceApplicationSerializer.Meta.fields)

    def test_service_application_serializer_includes_email(self):
        self.assertIn("email", ServiceApplicationSerializer.Meta.fields)

    def test_service_base_serializer_includes_has_location(self):
        self.assertIn("has_location", ServiceBaseSerializer.Meta.fields)

    def test_service_base_serializer_includes_show_location(self):
        self.assertIn("show_location", ServiceBaseSerializer.Meta.fields)

    def test_service_update_serializer_includes_show_location(self):
        self.assertIn("show_location", ServiceUpdateSerializer.Meta.fields)

    def test_has_location_is_true_when_address_present(self):
        serializer = ServiceBaseSerializer()
        service = SimpleNamespace(address="Ashgabat", latitude=None, longitude=None)

        self.assertTrue(serializer.get_has_location(service))

    def test_has_location_is_true_when_coordinates_present(self):
        serializer = ServiceBaseSerializer()
        service = SimpleNamespace(address="", latitude=37.95, longitude=58.38)

        self.assertTrue(serializer.get_has_location(service))

    def test_has_location_is_false_without_address_and_full_coordinates(self):
        serializer = ServiceBaseSerializer()
        service = SimpleNamespace(address=" ", latitude=37.95, longitude=None)

        self.assertFalse(serializer.get_has_location(service))
