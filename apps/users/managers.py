from django.contrib.auth.base_user import BaseUserManager
import re


class UserManager(BaseUserManager):
    use_in_migrations = True

    @staticmethod
    def normalize_phone(phone: str) -> str:
        digits = re.sub(r'\D+', '', phone or '')
        if not digits:
            return ''
        if not digits.startswith('993'):
            digits = '993' + digits
        return '+' + digits

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone must be set")
        phone = self.normalize_phone(phone)
        extra_fields.setdefault('is_active', True)
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra_fields):
        if not password:
            raise ValueError('Superuser must have a password.')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(phone, password, **extra_fields)
