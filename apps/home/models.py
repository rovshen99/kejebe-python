from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.regions.models import City


class HomePageConfig(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)

    city = models.ForeignKey(
        City,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="home_configs",
    )
    locale = models.CharField(max_length=10, default=None, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "id"]
        verbose_name = _("Home page config")
        verbose_name_plural = _("Home page configs")

    def __str__(self) -> str:
        return self.slug


class HomeBlockType(models.TextChoices):
    STORIES_ROW = "stories_row", _("Stories row")
    BANNER_CAROUSEL = "banner_carousel", _("Banner carousel")
    CATEGORY_STRIP = "category_strip", _("Category strip")
    SERVICE_CAROUSEL = "service_carousel", _("Service carousel")
    SERVICE_LIST = "service_list", _("Service list")


class HomeBlockSourceMode(models.TextChoices):
    MANUAL = "manual", _("Manual")
    QUERY = "query", _("Query")
    PINNED_QUERY = "pinned_query", _("Pinned + query")


class HomeBlock(models.Model):
    config = models.ForeignKey(HomePageConfig, on_delete=models.CASCADE, related_name="blocks")
    type = models.CharField(max_length=32, choices=HomeBlockType.choices)

    title_tm = models.CharField(max_length=255, blank=True, default="")
    title_ru = models.CharField(max_length=255, blank=True, default="")
    title_en = models.CharField(max_length=255, blank=True, default="")

    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    source_mode = models.CharField(
        max_length=16,
        choices=HomeBlockSourceMode.choices,
        default=HomeBlockSourceMode.QUERY,
    )

    query_params = models.JSONField(default=dict, blank=True)
    style = models.JSONField(default=dict, blank=True)
    limit = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Home block")
        verbose_name_plural = _("Home blocks")

    def __str__(self) -> str:
        return f"{self.get_type_display()} ({self.config.slug})"


class HomeBlockItem(models.Model):
    block = models.ForeignKey(HomeBlock, on_delete=models.CASCADE, related_name="manual_items")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Home block item")
        verbose_name_plural = _("Home block items")

    def __str__(self) -> str:
        return f"{self.block_id}: {self.content_object}"
