from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid

from apps.users.managers import UserManager
from apps.regions.models import City
from core.fields import WebPImageField


class RoleEnum(models.TextChoices):
    VENDOR = 'vendor', _("Vendor")
    CUSTOMER = 'customer', _("Customer")
    ADMIN = 'admin', _("Admin")


class User(AbstractBaseUser, PermissionsMixin):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name=_("UUID"))
    name = models.CharField(max_length=255, verbose_name=_("Name"), blank=True, null=True)
    surname = models.CharField(max_length=255, verbose_name=_("Surname"), blank=True, null=True)
    email = models.EmailField(unique=False, verbose_name=_("Email"), blank=True, null=True)
    password = models.CharField(max_length=255, verbose_name=_("Password"))
    phone = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name=_("Phone Number"),
    )

    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("City"),
        related_name="users",
    )

    avatar = WebPImageField(
        upload_to="users/avatars",
        verbose_name=_("Avatar"),
        null=True,
        blank=True,
        default=None,
    )

    role = models.CharField(
        max_length=20,
        choices=RoleEnum.choices,
        default=RoleEnum.CUSTOMER,
        verbose_name=_("Role")
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Deleted At"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ('-created_at',)

    def soft_delete(self):
        if self.deleted_at:
            return False

        now = timezone.now()
        old_phone = self.phone
        prefix = "deleted_"
        max_len = self._meta.get_field("phone").max_length
        suffix_len = max_len - len(prefix)
        if suffix_len <= 0:
            placeholder = str(self.id)[:max_len]
        else:
            placeholder = f"{prefix}{self.uuid.hex[:suffix_len]}"
            if self.__class__.objects.filter(phone=placeholder).exists():
                placeholder = f"{prefix}{uuid.uuid4().hex[:suffix_len]}"

        UserPhoneHistory.objects.create(
            user=self,
            phone=old_phone,
            assigned_at=self.created_at or now,
            revoked_at=now,
        )
        self.phone = placeholder
        self.name = None
        self.surname = None
        self.email = None
        self.avatar = None
        self.is_active = False
        self.deleted_at = now
        self.save(update_fields=[
            "phone",
            "name",
            "surname",
            "email",
            "avatar",
            "is_active",
            "deleted_at",
            "updated_at",
        ])
        return True

    def __str__(self):
        return f"{self.phone} - ({self.name or ''})"


class UserPhoneHistory(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="phone_history",
        verbose_name=_("User"),
    )
    phone = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name=_("Phone Number"),
    )
    assigned_at = models.DateTimeField(verbose_name=_("Assigned At"))
    revoked_at = models.DateTimeField(verbose_name=_("Revoked At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("User Phone History")
        verbose_name_plural = _("User Phone History")
        ordering = ("-revoked_at",)
