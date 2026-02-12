from __future__ import annotations

from core.utils import get_lang_code


class LangMixin:
    def _lang(self) -> str:
        if not hasattr(self, "_lang_code"):
            lang = None
            if hasattr(self, "context"):
                lang = self.context.get("lang")
                if not lang:
                    lang = get_lang_code(self.context.get("request"))
            self._lang_code = lang or get_lang_code()
        return self._lang_code
