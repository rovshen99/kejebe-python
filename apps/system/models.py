from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.services.models import ContactType


class SystemContact(models.Model):
    type = models.ForeignKey(
        ContactType,
        on_delete=models.CASCADE,
        verbose_name=_("Contact Type"),
        null=True,
        blank=True,
        related_name="system_contacts",
    )
    value = models.CharField(max_length=255, verbose_name=_("Contact Value"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    priority = models.PositiveIntegerField(default=100, verbose_name=_("Priority"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("System Contact")
        verbose_name_plural = _("System Contacts")
        ordering = ("priority", "id")

    def __str__(self):
        if self.type_id:
            return f"{self.type.slug}: {self.value}"
        return self.value
