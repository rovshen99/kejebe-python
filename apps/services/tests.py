from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from rest_framework import serializers

from apps.services.admin import ServiceVideoAdminForm
from apps.services.management.commands.generate_hls import Command as GenerateHLSCommand
from apps.categories.models import Category
from apps.services.models import (
    Attribute,
    AttributeOption,
    CategoryAttribute,
    ProductAttributeValue,
    Service,
    ServiceAttributeValue,
    ServiceProduct,
    ServiceVideo,
)
from core.utils import format_price_text
from apps.services.serializers import (
    AttributeSerializer,
    CategorySchemaSerializer,
    CategorySchemaAttributeSerializer,
    ServiceApplicationSerializer,
    ServiceDetailSerializer,
    ServiceBaseSerializer,
    ServiceShowcaseSerializer,
    ServiceUpdateSerializer,
)
from apps.services.throttles import ServiceApplicationIPThrottle
from apps.users.models import RoleEnum, User


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


class GenerateHLSCommandTests(SimpleTestCase):
    @override_settings(DELETE_ORIGINAL_VIDEO_AFTER_HLS=True)
    @patch("apps.services.management.commands.generate_hls.default_storage.delete")
    def test_deletes_original_source_after_hls_ready(self, delete_mock):
        command = GenerateHLSCommand()
        video = Mock()
        video.pk = 7
        video.hls_ready = True
        video.file.name = "services/videos/source.mov"

        command._delete_original_file_if_configured(video)

        delete_mock.assert_called_once_with("services/videos/source.mov")
        self.assertIsNone(video.file)
        video.save.assert_called_once_with(update_fields=["file"])

    @override_settings(DELETE_ORIGINAL_VIDEO_AFTER_HLS=False)
    @patch("apps.services.management.commands.generate_hls.default_storage.delete")
    def test_keeps_original_source_when_setting_disabled(self, delete_mock):
        command = GenerateHLSCommand()
        video = Mock()
        video.pk = 7
        video.hls_ready = True
        video.file.name = "services/videos/source.mov"

        command._delete_original_file_if_configured(video)

        delete_mock.assert_not_called()
        video.save.assert_not_called()

    @patch("apps.services.management.commands.generate_hls.ServiceVideo.objects")
    def test_cleanup_originals_only_targets_hls_ready_videos(self, objects_mock):
        command = GenerateHLSCommand()
        video = Mock()
        queryset = Mock()
        queryset.exclude.return_value = queryset
        queryset.filter.return_value = queryset
        queryset.exists.return_value = True
        queryset.__iter__ = Mock(return_value=iter([video]))
        objects_mock.filter.return_value = queryset

        with patch.object(command, "_delete_original_file_if_configured") as delete_original_mock:
            command._cleanup_originals(video_id=11, limit=0)

        objects_mock.filter.assert_called_once_with(hls_ready=True)
        queryset.filter.assert_called_once_with(pk=11)
        delete_original_mock.assert_called_once_with(video)

    @patch("apps.services.management.commands.generate_hls.ServiceVideo.objects")
    def test_handle_cleanup_originals_does_not_resolve_ffmpeg(self, objects_mock):
        command = GenerateHLSCommand()
        queryset = Mock()
        queryset.exclude.return_value = queryset
        queryset.filter.return_value = queryset
        queryset.exists.return_value = False
        objects_mock.filter.return_value = queryset

        with patch.object(command, "_resolve_ffmpeg_bin") as resolve_mock:
            command.handle(cleanup_originals=True, video_id=None, force=False, limit=0, ffmpeg_bin="")

        resolve_mock.assert_not_called()


class ServiceVideoAdminFormTests(SimpleTestCase):
    def test_existing_video_does_not_require_file_field(self):
        form = ServiceVideoAdminForm(instance=ServiceVideo(pk=5))

        self.assertFalse(form.fields["file"].required)

    def test_new_video_without_file_still_requires_upload(self):
        form = ServiceVideoAdminForm(
            data={"position": 1},
            instance=ServiceVideo(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)


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

    def test_service_detail_serializer_includes_attributes(self):
        self.assertIn("attributes", ServiceDetailSerializer.Meta.fields)

    def test_service_detail_serializer_includes_media(self):
        self.assertIn("media", ServiceDetailSerializer.Meta.fields)

    def test_service_update_serializer_includes_show_location(self):
        self.assertIn("show_location", ServiceUpdateSerializer.Meta.fields)

    def test_category_schema_serializer_exposes_service_and_product_attributes(self):
        serializer = CategorySchemaSerializer()

        self.assertIn("service_attributes", serializer.fields)
        self.assertIn("product_attributes", serializer.fields)

    def test_category_schema_attribute_serializer_exposes_ui_metadata(self):
        serializer = CategorySchemaAttributeSerializer()

        self.assertIn("icon", serializer.fields)
        self.assertIn("section", serializer.fields)
        self.assertIn("unit", serializer.fields)
        self.assertIn("unit_tm", serializer.fields)
        self.assertIn("unit_ru", serializer.fields)
        self.assertIn("placeholder", serializer.fields)
        self.assertIn("help_text", serializer.fields)
        self.assertIn("show_in_filters", serializer.fields)
        self.assertIn("show_in_card", serializer.fields)
        self.assertIn("show_in_detail", serializer.fields)
        self.assertIn("filter_type", serializer.fields)
        self.assertIn("filter_order", serializer.fields)

    def test_attribute_serializer_localizes_unit(self):
        request = RequestFactory().get("/api/v1/categories/1/schema/", HTTP_ACCEPT_LANGUAGE="ru")
        serializer = AttributeSerializer(
            instance=SimpleNamespace(
                id=1,
                name_tm="Sygymdarlyk",
                name_ru="Вместимость",
                icon=SimpleNamespace(url="https://cdn.example.com/capacity.svg"),
                slug="capacity",
                input_type="number",
                unit_tm="myhman",
                unit_ru="гостей",
                placeholder_tm="",
                placeholder_ru="",
                help_text_tm="",
                help_text_ru="",
                min_value=None,
                max_value=None,
                step=None,
            ),
            context={"request": request},
        )

        self.assertEqual(serializer.data["unit"], "гостей")
        self.assertEqual(serializer.data["icon"], "https://cdn.example.com/capacity.svg")

    def test_category_schema_attribute_serializer_localizes_unit(self):
        request = RequestFactory().get("/api/v1/categories/1/schema/", HTTP_ACCEPT_LANGUAGE="ru")
        serializer = CategorySchemaAttributeSerializer(
            instance={
                "id": 1,
                "slug": "capacity",
                "name_tm": "Sygymdarlyk",
                "name_ru": "Вместимость",
                "icon": SimpleNamespace(url="https://cdn.example.com/capacity.svg"),
                "input_type": "number",
                "unit_tm": "myhman",
                "unit_ru": "гостей",
                "placeholder_tm": "",
                "placeholder_ru": "",
                "help_text_tm": "",
                "help_text_ru": "",
                "min_value": None,
                "max_value": None,
                "step": None,
                "scope": "product",
                "section_tm": "",
                "section_ru": "",
                "is_required": True,
                "is_filterable": True,
                "is_highlighted": True,
                "show_in_filters": True,
                "show_in_card": True,
                "show_in_detail": True,
                "filter_type": "range",
                "filter_order": 100,
                "sort_order": 100,
                "options": [],
            },
            context={"request": request},
        )

        self.assertEqual(serializer.data["unit"], "гостей")
        self.assertEqual(serializer.data["icon"], "https://cdn.example.com/capacity.svg")

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


class ServiceAttributeFilterTests(TestCase):
    def setUp(self):
        self.vendor = User.objects.create(phone="+99361000001", password="x", role=RoleEnum.VENDOR)
        self.category = Category.objects.create(name_tm="Toý mekany", name_ru="Ресторан", slug="restaurant")

        self.service_a = Service.objects.create(
            vendor=self.vendor,
            category=self.category,
            title_tm="A",
            title_ru="A",
            description_tm="A",
            description_ru="A",
            is_active=True,
        )
        self.service_b = Service.objects.create(
            vendor=self.vendor,
            category=self.category,
            title_tm="B",
            title_ru="B",
            description_tm="B",
            description_ru="B",
            is_active=True,
        )
        self.service_c = Service.objects.create(
            vendor=self.vendor,
            category=self.category,
            title_tm="C",
            title_ru="C",
            description_tm="C",
            description_ru="C",
            is_active=True,
        )

        self.parking = Attribute.objects.create(
            name_tm="Awtoulag duralgasy",
            name_ru="Парковка",
            slug="parking",
            input_type="boolean",
            is_active=True,
        )
        self.capacity = Attribute.objects.create(
            name_tm="Sygymdarlyk",
            name_ru="Вместимость",
            slug="capacity",
            input_type="number",
            unit_tm="myhman",
            unit_ru="гостей",
            is_active=True,
        )
        self.hall_shape = Attribute.objects.create(
            name_tm="Zalyň görnüşi",
            name_ru="Форма зала",
            slug="hall_shape",
            input_type="choice",
            is_active=True,
        )
        self.round_option = AttributeOption.objects.create(
            attribute=self.hall_shape,
            value="round",
            label_tm="Tegelek",
            label_ru="Круглый",
        )
        self.square_option = AttributeOption.objects.create(
            attribute=self.hall_shape,
            value="square",
            label_tm="Kwadrat",
            label_ru="Квадратный",
        )

        CategoryAttribute.objects.create(
            category=self.category,
            attribute=self.parking,
            scope=CategoryAttribute.Scope.SERVICE,
            is_filterable=True,
        )
        CategoryAttribute.objects.create(
            category=self.category,
            attribute=self.capacity,
            scope=CategoryAttribute.Scope.PRODUCT,
            is_filterable=True,
        )
        CategoryAttribute.objects.create(
            category=self.category,
            attribute=self.hall_shape,
            scope=CategoryAttribute.Scope.PRODUCT,
            is_filterable=True,
        )

        ServiceAttributeValue.objects.create(
            service=self.service_a,
            attribute=self.parking,
            value_boolean=True,
        )
        ServiceAttributeValue.objects.create(
            service=self.service_b,
            attribute=self.parking,
            value_boolean=False,
        )

        hall_a = ServiceProduct.objects.create(service=self.service_a, title_tm="A1", title_ru="A1", price=1000)
        ProductAttributeValue.objects.create(product=hall_a, attribute=self.capacity, value_number=320)
        ProductAttributeValue.objects.create(product=hall_a, attribute=self.hall_shape, option=self.round_option)

        hall_b1 = ServiceProduct.objects.create(service=self.service_b, title_tm="B1", title_ru="B1", price=1000)
        ProductAttributeValue.objects.create(product=hall_b1, attribute=self.capacity, value_number=350)
        ProductAttributeValue.objects.create(product=hall_b1, attribute=self.hall_shape, option=self.square_option)

        hall_b2 = ServiceProduct.objects.create(service=self.service_b, title_tm="B2", title_ru="B2", price=1000)
        ProductAttributeValue.objects.create(product=hall_b2, attribute=self.capacity, value_number=120)
        ProductAttributeValue.objects.create(product=hall_b2, attribute=self.hall_shape, option=self.round_option)

    def _service_ids(self, response):
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        return {item["id"] for item in payload["results"]}

    def test_service_attribute_boolean_filter_works(self):
        response = self.client.get("/api/v1/services/", {"service_attr.parking": "true"})

        self.assertEqual(self._service_ids(response), {self.service_a.id})

    def test_product_attribute_filters_apply_to_same_product(self):
        response = self.client.get(
            "/api/v1/services/",
            {
                "product_attr.capacity_min": "300",
                "product_attr.hall_shape": "round",
            },
        )

        self.assertEqual(self._service_ids(response), {self.service_a.id})

    def test_product_choice_filter_supports_csv_or_semantics(self):
        response = self.client.get("/api/v1/services/", {"product_attr.hall_shape": "round,square"})

        self.assertEqual(self._service_ids(response), {self.service_a.id, self.service_b.id})
