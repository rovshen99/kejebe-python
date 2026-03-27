from django.test import SimpleTestCase

from core.utils import format_price_text


class FormatPriceTextTests(SimpleTestCase):
    def test_price_on_request_respects_russian_language(self):
        self.assertEqual(format_price_text(None, None, lang="ru"), "Цена по запросу")

    def test_price_on_request_respects_turkmen_language(self):
        self.assertEqual(format_price_text(None, None, lang="tm"), "Bahasy soralanda")
