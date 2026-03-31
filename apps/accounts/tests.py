from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from apps.accounts.models import SMSChallenge
from apps.accounts.views import ConfirmReverseSMSView, InitReverseSMSView
from apps.users.models import User


@override_settings(
    SMS_BYPASS_ENABLED=True,
    SMS_BYPASS_NUMBERS=["+99371111111"],
    SMS_SERVICE_NUMBER="+99361111111",
)
class SMSBypassAuthFlowTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_init_returns_skip_sms_for_review_phone(self):
        request = self.factory.post("/auth/sms/init/", {"phone": "+99371111111"}, format="json")

        response = InitReverseSMSView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["skip_sms"])
        self.assertEqual(response.data["phone_number"], "+99361111111")
        self.assertEqual(SMSChallenge.objects.count(), 1)

    def test_init_keeps_regular_sms_flow_for_regular_phone(self):
        request = self.factory.post("/auth/sms/init/", {"phone": "+99371234567"}, format="json")

        response = InitReverseSMSView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["skip_sms"])

    @patch("apps.accounts.views.issue_tokens", return_value={"refresh": "refresh-token", "access": "access-token"})
    @patch("apps.accounts.views.get_or_create_user_from_validated")
    def test_confirm_auto_verifies_review_phone_without_sms(self, get_or_create_user_mock, issue_tokens_mock):
        user = User.objects.create(phone="+99371111111", password="review-password")
        get_or_create_user_mock.return_value = (user, False)
        challenge = SMSChallenge.create("+99371111111", "+99361111111", 600)

        request = self.factory.post(
            "/auth/sms/confirm/",
            {"challenge_id": str(challenge.id)},
            format="json",
        )

        response = ConfirmReverseSMSView.as_view()(request)
        challenge.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["verified"])
        self.assertEqual(response.data["tokens"]["access"], "access-token")
        self.assertTrue(challenge.is_verified)
