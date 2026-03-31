"""
cbr_rate.py — получение курса USD/RUB с API Центробанка РФ.
"""
import logging
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)

CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"


def get_usd_rub_rate() -> float:
    """Возвращает курс USD/RUB по данным ЦБ РФ. При ошибке возвращает 90.0."""
    try:
        resp = requests.get(CBR_URL, timeout=10)
        resp.raise_for_status()
        # ЦБ РФ отдаёт XML в windows-1251; парсим из байт — ET сам читает encoding из заголовка XML
        root = ET.fromstring(resp.content)
        for valute in root.findall("Valute"):
            char_code = valute.find("CharCode")
            if char_code is not None and char_code.text == "USD":
                value = valute.find("Value")
                if value is not None:
                    rate = float(value.text.replace(",", "."))
                    logger.info("Курс USD/RUB от ЦБ РФ: %.4f", rate)
                    return rate
    except Exception as e:
        logger.warning("Не удалось получить курс ЦБ РФ: %s. Используется 90.0", e)
    return 90.0
