from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.categories.models import Category
from apps.regions.models import City, Region
from apps.services.models import Review, Service
from apps.stories.models import ServiceStory
from apps.users.models import User, UserBlock, UserModerationEvent


_GIF_1PX = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
    b"\xff\xff\xff!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class UserBlockingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.blocker = User.objects.create_user(phone="+99361111111", password="pass123")
        self.blocked = User.objects.create_user(phone="+99362222222", password="pass123")
        self.third = User.objects.create_user(phone="+99363333333", password="pass123")

    def test_block_requires_authentication(self):
        response = self.client.post(f"/api/v1/users/{self.blocked.id}/block/")

        self.assertEqual(response.status_code, 401)

    def test_block_user_is_idempotent_and_logs_event(self):
        self.client.force_authenticate(user=self.blocker)

        first = self.client.post(f"/api/v1/users/{self.blocked.id}/block/")
        second = self.client.post(f"/api/v1/users/{self.blocked.id}/block/")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["blocked_user_id"], str(self.blocked.uuid))
        self.assertTrue(first.data["is_blocked"])
        self.assertEqual(UserBlock.objects.count(), 1)
        self.assertEqual(
            UserModerationEvent.objects.filter(action=UserModerationEvent.Action.BLOCK).count(),
            1,
        )

    def test_block_self_returns_400(self):
        self.client.force_authenticate(user=self.blocker)

        response = self.client.post(f"/api/v1/users/{self.blocker.id}/block/")

        self.assertEqual(response.status_code, 400)

    def test_delete_unblock_and_list(self):
        UserBlock.objects.create(blocker=self.blocker, blocked=self.blocked)
        self.client.force_authenticate(user=self.blocker)

        listed = self.client.get("/api/v1/users/blocked/")
        removed = self.client.delete(f"/api/v1/users/{self.blocked.id}/block/")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]["blocked_user_id"], str(self.blocked.uuid))
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(removed.data["is_blocked"])
        self.assertFalse(UserBlock.objects.filter(blocker=self.blocker, blocked=self.blocked).exists())
        self.assertEqual(
            UserModerationEvent.objects.filter(action=UserModerationEvent.Action.UNBLOCK).count(),
            1,
        )

    def test_block_unknown_user_returns_404(self):
        self.client.force_authenticate(user=self.blocker)

        response = self.client.post("/api/v1/users/999999/block/")

        self.assertEqual(response.status_code, 404)


class BlockedUgcFilteringTests(TestCase):
    def setUp(self):
        self.bleach_clean_patcher = patch(
            "django_summernote.fields.bleach.clean",
            side_effect=lambda *args, **kwargs: args[0] if args else "",
        )
        self.bleach_clean_patcher.start()
        self.addCleanup(self.bleach_clean_patcher.stop)

        self.client = APIClient()
        self.blocker = User.objects.create_user(phone="+99364444444", password="pass123")
        self.blocked_author = User.objects.create_user(phone="+99365555555", password="pass123")
        self.allowed_author = User.objects.create_user(phone="+99366666666", password="pass123")
        self.blocked_vendor = User.objects.create_user(
            phone="+99367777777",
            password="pass123",
            role="vendor",
        )
        self.allowed_vendor = User.objects.create_user(
            phone="+99368888888",
            password="pass123",
            role="vendor",
        )

        self.region = Region.objects.create(name_tm="Ahal", name_ru="Ахал")
        self.city = City.objects.create(region=self.region, name_tm="Ashgabat", name_ru="Ашхабад")
        self.category = Category.objects.create(name_tm="Test", name_ru="Тест")

        self.service = Service.objects.create(
            vendor=self.allowed_vendor,
            category=self.category,
            city=self.city,
            title_tm="Service",
            title_ru="Service",
            description_tm="Desc",
            description_ru="Desc",
            is_active=True,
        )
        self.blocked_vendor_service = Service.objects.create(
            vendor=self.blocked_vendor,
            category=self.category,
            city=self.city,
            title_tm="Blocked Story Service",
            title_ru="Blocked Story Service",
            description_tm="Desc",
            description_ru="Desc",
            is_active=True,
        )
        self.allowed_vendor_service = Service.objects.create(
            vendor=self.allowed_vendor,
            category=self.category,
            city=self.city,
            title_tm="Allowed Story Service",
            title_ru="Allowed Story Service",
            description_tm="Desc",
            description_ru="Desc",
            is_active=True,
        )

        Review.objects.create(
            user=self.blocked_author,
            service=self.service,
            rating=5,
            comment="blocked review",
            is_approved=True,
        )
        Review.objects.create(
            user=self.allowed_author,
            service=self.service,
            rating=4,
            comment="allowed review",
            is_approved=True,
        )

        ServiceStory.objects.create(
            service=self.blocked_vendor_service,
            title="blocked story",
            image=SimpleUploadedFile("blocked.gif", _GIF_1PX, content_type="image/gif"),
            is_active=True,
        )
        ServiceStory.objects.create(
            service=self.allowed_vendor_service,
            title="allowed story",
            image=SimpleUploadedFile("allowed.gif", _GIF_1PX, content_type="image/gif"),
            is_active=True,
        )

        UserBlock.objects.create(blocker=self.blocker, blocked=self.blocked_author)
        UserBlock.objects.create(blocker=self.blocker, blocked=self.blocked_vendor)

        self.client.force_authenticate(user=self.blocker)

    def test_review_list_excludes_blocked_authors(self):
        response = self.client.get(f"/api/v1/reviews/?service={self.service.id}")

        self.assertEqual(response.status_code, 200)
        ids = [item["user"]["uuid"] for item in response.data["results"]]
        self.assertIn(str(self.allowed_author.uuid), ids)
        self.assertNotIn(str(self.blocked_author.uuid), ids)

    def test_stories_list_excludes_blocked_vendor_content(self):
        response = self.client.get("/api/v1/stories/")

        self.assertEqual(response.status_code, 200)
        returned_service_ids = {item["service"] for item in response.data}
        self.assertIn(self.allowed_vendor_service.id, returned_service_ids)
        self.assertNotIn(self.blocked_vendor_service.id, returned_service_ids)
