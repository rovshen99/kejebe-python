from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_summernote.fields import SummernoteTextField

from apps.services.models import ContactType, Service


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


class ClientFeedback(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("New")
        PROCESSED = "processed", _("Processed")

    name = models.CharField(max_length=255, verbose_name=_("Name"))
    phone = models.CharField(max_length=32, db_index=True, verbose_name=_("Phone Number"))
    message = models.TextField(verbose_name=_("Message"))
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Client Feedback")
        verbose_name_plural = _("Client Feedback")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class SystemAbout(models.Model):
    about_tm = SummernoteTextField(verbose_name=_("About (TM)"))
    about_ru = SummernoteTextField(verbose_name=_("About (RU)"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("System About")
        verbose_name_plural = _("System About")
        ordering = ("-updated_at", "-id")

    def save(self, *args, **kwargs):
        if not self.pk and SystemAbout.objects.exists():
            raise ValidationError("Only one System About record is allowed.")
        return super().save(*args, **kwargs)

    def __str__(self):
        return "System About"


class WebsiteShowcaseConfig(models.Model):
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    limit = models.PositiveSmallIntegerField(default=4, verbose_name=_("Limit"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Website Showcase")
        verbose_name_plural = _("Website Showcase")
        ordering = ("-updated_at", "-id")

    def clean(self):
        if self.limit < 1 or self.limit > 8:
            raise ValidationError({"limit": _("Limit must be between 1 and 8.")})
        if not self.pk and WebsiteShowcaseConfig.objects.exists():
            raise ValidationError(_("Only one Website Showcase record is allowed."))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Website Showcase"


class WebsiteShowcaseItem(models.Model):
    config = models.ForeignKey(
        WebsiteShowcaseConfig,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Config"),
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="website_showcase_items",
        verbose_name=_("Service"),
    )
    position = models.PositiveIntegerField(default=100, verbose_name=_("Position"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        verbose_name = _("Website Showcase Item")
        verbose_name_plural = _("Website Showcase Items")
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("config", "service"),
                name="website_showcase_config_service_unique",
            ),
        ]

    def __str__(self):
        return f"{self.position}: {self.service}"
