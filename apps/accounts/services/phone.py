import re
from django.conf import settings


def normalize_phone(raw: str) -> str:
    digits = re.sub(r'\D+', '', raw or '')
    if not digits:
        return ''
    cc = getattr(settings, 'DEFAULT_PHONE_COUNTRY_CODE', '993')
    if not digits.startswith(cc):
        digits = cc + digits
    return '+' + digits


def is_bypass_number(phone: str) -> bool:
    from django.conf import settings
    if not getattr(settings, "SMS_BYPASS_ENABLED", False):
        return False
    phone_norm = normalize_phone(phone)
    bypass = {normalize_phone(n) for n in getattr(settings, "SMS_BYPASS_NUMBERS", [])}
    return phone_norm in bypass
