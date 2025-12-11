from typing import Any, Iterable, Optional, Set

from django.utils import translation
from django.utils.translation import get_language_from_request

SUPPORTED_LANGS: Set[str] = {"tm", "ru", "en"}


def get_lang_code(request=None, supported: Iterable[str] = None, default: str = "tm") -> str:
    supported_set = set(supported or SUPPORTED_LANGS)
    lang = None

    if request is not None:
        header = request.META.get("HTTP_ACCEPT_LANGUAGE")
        if header:
            for part in header.split(","):
                candidate = part.split(";")[0].strip()
                if not candidate:
                    continue
                short = candidate.split("-")[0]
                if short in supported_set:
                    lang = short
                    break

        if not lang:
            detected = get_language_from_request(request)
            if detected:
                short = detected.split("-")[0]
                if short in supported_set:
                    lang = short

        if not lang:
            qp_lang = None
            if hasattr(request, "query_params"):
                qp_lang = request.query_params.get("lang")
            if not qp_lang and hasattr(request, "GET"):
                qp_lang = request.GET.get("lang")
            if qp_lang:
                short = qp_lang.split("-")[0]
                if short in supported_set:
                    lang = short
    if not lang:
        lang = translation.get_language() or default
    lang = lang.split("-")[0]
    return lang if lang in supported_set else default


def localized_value(obj: Any, prefix: str, lang: Optional[str] = None, default: str = "tm") -> Optional[str]:
    if obj is None:
        return None
    lang = lang or get_lang_code(default=default)
    field_name = f"{prefix}_{lang}" if lang in SUPPORTED_LANGS else f"{prefix}_{default}"
    return getattr(obj, field_name, None)


def _format_number(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num.is_integer():
        return str(int(num))
    return f"{num:.0f}"


def format_price_text(price_min: Any, price_max: Any, currency: str = "TMT") -> str:
    formatted_min = _format_number(price_min)
    formatted_max = _format_number(price_max)

    if formatted_min and formatted_max:
        if formatted_min == formatted_max:
            return f"{formatted_min} {currency}"
        return f"{formatted_min}–{formatted_max} {currency}"
    if formatted_min:
        return f"от {formatted_min} {currency}"
    if formatted_max:
        return f"до {formatted_max} {currency}"
    return "Цена по запросу"
