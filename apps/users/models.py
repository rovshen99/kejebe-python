from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

from apps.users.managers import UserManager


class RoleEnum(models.TextChoices):
    VENDOR = 'vendor', _("Vendor")
    CUSTOMER = 'customer', _("Customer")
    ADMIN = 'admin', _("Admin")


class User(AbstractBaseUser, PermissionsMixin):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name=_("UUID"))
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    surname = models.CharField(max_length=255, verbose_name=_("Surname"), blank=True, null=True)
    email = models.EmailField(unique=True, verbose_name=_("Email"))
    password = models.CharField(max_length=255, verbose_name=_("Password"))
    phone = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name=_("Phone Number"),
    )

    role = models.CharField(
        max_length=20,
        choices=RoleEnum.choices,
        default=RoleEnum.CUSTOMER,
        verbose_name=_("Role")
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.phone} - ({self.name or ""})"
