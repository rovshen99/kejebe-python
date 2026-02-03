from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.fields import WebPImageField
from apps.regions.models import Region, City


class BannerQuerySet(models.QuerySet):
    def active_now(self, now=None):
        if now is None:
            now = timezone.now()
        return self.filter(
            is_active=True
        ).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now),
        )


class Banner(models.Model):
    title_tm = models.CharField(max_length=255, verbose_name=_("Title (TM)"))
    title_ru = models.CharField(max_length=255, verbose_name=_("Title (RU)"))

    image = WebPImageField(upload_to="banners/", verbose_name=_("Image"))
    open_type = models.CharField(
        max_length=20,
        choices=[
            ("service", _("Service")),
            ("search", _("Search")),
            ("navigate", _("Navigate")),
            ("url", _("URL")),
        ],
        null=True,
        blank=True,
        verbose_name=_("Open Type"),
    )
    open_params = models.JSONField(default=dict, blank=True, verbose_name=_("Open Params"))

    regions = models.ManyToManyField(Region, related_name='banners', blank=True, verbose_name=_("Regions"))
    cities = models.ManyToManyField(City, related_name='banners', blank=True, verbose_name=_("Cities"))

    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Starts At"))
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Ends At"))

    priority = models.PositiveIntegerField(default=100, verbose_name=_("Priority"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Banner")
        verbose_name_plural = _("Banners")
        ordering = ("priority", "-created_at")

    def __str__(self):
        return self.title_tm

    objects = BannerQuerySet.as_manager()
