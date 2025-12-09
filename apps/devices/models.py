from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.users.models import User
from apps.regions.models import City


class Device(models.Model):
    class Platform(models.TextChoices):
        IOS = "ios", _("iOS")
        ANDROID = "android", _("Android")
        WEB = "web", _("Web")
        UNKNOWN = "unknown", _("Unknown")

    device_id = models.CharField(max_length=128, unique=True, verbose_name=_("Device ID"))
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.UNKNOWN,
        verbose_name=_("Platform")
    )
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="devices",
        verbose_name=_("User")
    )
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
        verbose_name=_("City")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    last_seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Seen At"))

    class Meta:
        verbose_name = _("Device")
        verbose_name_plural = _("Devices")

    def __str__(self):
        return self.device_id
