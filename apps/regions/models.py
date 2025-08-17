from django.db import models
from django.utils.translation import gettext_lazy as _


class Region(models.Model):
    name_tm = models.CharField(max_length=255, verbose_name=_("Name (TM)"))
    name_ru = models.CharField(max_length=255, verbose_name=_("Name (RU)"))
    name_en = models.CharField(max_length=255, verbose_name=_("Name (EN)"))

    class Meta:
        verbose_name = _("Region")
        verbose_name_plural = _("Regions")
        ordering = ('name_tm',)

    def __str__(self):
        return self.name_tm


class City(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name=_("Region"))
    name_tm = models.CharField(max_length=255, verbose_name=_("Name (TM)"))
    name_ru = models.CharField(max_length=255, verbose_name=_("Name (RU)"))
    name_en = models.CharField(max_length=255, verbose_name=_("Name (EN)"))

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        ordering = ('region', 'name_tm')
        unique_together = ('region', 'name_tm')

    def __str__(self):
        return self.name_tm
