from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
import uuid


class InboundSMS(models.Model):
    provider = models.CharField(max_length=32, blank=True, default="")
    provider_message_id = models.CharField(max_length=128, blank=True, default="")
    from_number = models.CharField(max_length=32, db_index=True)
    to_number = models.CharField(max_length=32, db_index=True)
    body = models.TextField(blank=True, default="")
    received_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-received_at",)


class SMSChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_number = models.CharField(max_length=32, db_index=True)
    to_number = models.CharField(max_length=32, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    @property
    def is_verified(self): return self.verified_at is not None
    @property
    def is_expired(self):  return timezone.now() >= self.expires_at

    @classmethod
    def create(cls, from_number:str, to_number:str, ttl_sec:int=600):
        return cls.objects.create(
            from_number=from_number,
            to_number=to_number,
            expires_at=timezone.now() + timedelta(seconds=ttl_sec),
        )
