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


class AccountDeletionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSED = "processed", _("Processed")

    phone = models.CharField(max_length=32, db_index=True, verbose_name=_("Phone Number"))
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Account Deletion Request")
        verbose_name_plural = _("Account Deletion Requests")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.phone} ({self.status})"
