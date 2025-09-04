from django.db import models
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from core.fields import WebPImageField


class Category(MPTTModel):
    name_tm = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)

    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent"),
    )

    slug = models.SlugField(
        max_length=64, unique=True, blank=True, null=True, verbose_name=_("Slug")
    )
    image = WebPImageField(
        upload_to="category/", verbose_name=_("Image"), null=True, default=None, blank=True
    )
    icon = WebPImageField(
        upload_to="category/icons/", verbose_name=_("Icon"), null=True, blank=True, default=None
    )
    priority = models.PositiveIntegerField(default=100, verbose_name=_("Priority"))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ("priority",)

    class MPTTMeta:
        order_insertion_by = ["name_tm"]

    def __str__(self):
        return self.name_tm
