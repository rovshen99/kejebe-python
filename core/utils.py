from typing import Any, Iterable, Optional, Set, Union

from django.utils import translation
from django.utils.translation import get_language_from_request, gettext as _

SUPPORTED_LANGS: Set[str] = {"tm", "ru"}


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


NumberLike = Union[int, float, str, None]


def _format_price_value(value: NumberLike) -> Optional[str]:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return f"{num:.0f}"


def format_price_text(
    price_min: NumberLike,
    price_max: NumberLike,
    currency: str = "TMT",
    lang: Optional[str] = None,
) -> str:
    formatted_min = _format_price_value(price_min)
    formatted_max = _format_price_value(price_max)
    lang_code = (lang or get_lang_code(default="tm")).split("-")[0]

    with translation.override(lang_code):
        if formatted_min is not None and formatted_max is not None:
            if formatted_min == formatted_max:
                return _("%(price)s %(currency)s") % {
                    "price": formatted_min,
                    "currency": currency,
                }
            return _("%(price_min)s–%(price_max)s %(currency)s") % {
                "price_min": formatted_min,
                "price_max": formatted_max,
                "currency": currency,
            }

        if formatted_min is not None:
            return _("from %(price)s %(currency)s") % {
                "price": formatted_min,
                "currency": currency,
            }

        if formatted_max is not None:
            return _("up to %(price)s %(currency)s") % {
                "price": formatted_max,
                "currency": currency,
            }

        return _("Price on request")
