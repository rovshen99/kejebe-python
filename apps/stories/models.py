from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _

from apps.services.models import Service
from apps.users.models import User
from apps.devices.models import Device
from core.fields import WebPImageField


class ServiceStory(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="stories",
        verbose_name=_("Service")
    )
    title = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Title"))
    caption = models.TextField(null=True, blank=True, verbose_name=_("Caption"))
    image = WebPImageField(upload_to="services/stories", verbose_name=_("Image"))

    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Starts At"))
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Ends At"))

    priority = models.PositiveIntegerField(default=100, verbose_name=_("Priority"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Service Story")
        verbose_name_plural = _("Service Stories")
        ordering = ("priority", "-starts_at", "-created_at")

    def __str__(self):
        return self.title or f"Story #{self.pk}"

    @property
    def is_active_now(self):
        now = timezone.now()
        return bool(
            self.is_active
            and (self.starts_at is None or self.starts_at <= now)
            and (self.ends_at is None or self.ends_at >= now)
        )

    def save(self, *args, **kwargs):
        ttl_hours = getattr(settings, "SERVICE_STORY_TTL_HOURS", 24)
        if not self.starts_at:
            self.starts_at = timezone.now()
        if not self.ends_at:
            self.ends_at = self.starts_at + timedelta(hours=ttl_hours)
        super().save(*args, **kwargs)


class ServiceStoryView(models.Model):
    story = models.ForeignKey(
        ServiceStory,
        on_delete=models.CASCADE,
        related_name="views",
        verbose_name=_("Story")
    )
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="story_views",
        verbose_name=_("User")
    )
    device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="story_views",
        verbose_name=_("Device")
    )
    viewed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Viewed At"))

    class Meta:
        verbose_name = _("Service Story View")
        verbose_name_plural = _("Service Story Views")
        constraints = [
            models.UniqueConstraint(
                fields=["story", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_story_view_per_user",
            ),
            models.UniqueConstraint(
                fields=["story", "device"],
                condition=models.Q(device__isnull=False, user__isnull=True),
                name="unique_story_view_per_device",
            ),
        ]

    def __str__(self):
        viewer = self.user or self.device or "anon"
        return f"{self.story_id} viewed by {viewer}"

# Create your models here.
