"""
Пробив госномера автомобиля через публичные API ГИБДД
  - ГИБДД check/auto  (ограничения, розыск)
  - ЕАИСТО           (технический осмотр)
Оба эндпоинта без ключей; возможна CAPTCHA — обрабатываем gracefully.
"""
import logging
import re

import httpx

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

_GIBDD_URL = "https://xn--90adear.xn--p1ai/check/auto"   # gibdd.ru
_EAISTO_URL = "https://eaisto.gibdd.ru/webreq/RequestEAISTO.json"

# Допустимые кириллические буквы в российском номере
_ALLOWED_CYR = set("АВЕКМНОРСТУХ")
# Транслит латиница → кириллица (для нормализации)
_LAT_TO_CYR = {
    "A": "А", "B": "В", "E": "Е", "K": "К", "M": "М",
    "H": "Н", "O": "О", "P": "Р", "C": "С", "T": "Т",
    "Y": "У", "X": "Х",
}


def normalize_plate(plate: str) -> str:
    """
    Приводит госномер к стандартному виду:
    - uppercase
    - убирает пробелы и дефисы
    - заменяет похожие латинские буквы кириллическими
    """
    plate = plate.upper().replace(" ", "").replace("-", "")
    normalized = []
    for ch in plate:
        normalized.append(_LAT_TO_CYR.get(ch, ch))
    result = "".join(normalized)
    log.debug("normalize_plate: %r → %r", plate, result)
    return result


def _parse_gibdd_response(data: dict) -> dict:
    """Извлекает ограничения и признак розыска из ответа ГИБДД."""
    restrictions = []
    wanted = False

    # ГИБДД возвращает вложенный dict с различными блоками
    # Структура может различаться — обходим рекурсивно
    def _walk(obj, path=""):
        nonlocal wanted
        if isinstance(obj, dict):
            for k, v in obj.items():
                key_lower = str(k).lower()
                if "розыск" in key_lower or "wanted" in key_lower:
                    if v and str(v).lower() not in ("нет", "false", "0", ""):
                        wanted = True
                if "ограничен" in key_lower or "запрет" in key_lower or "арест" in key_lower:
                    if v and str(v).lower() not in ("нет", "false", "0", ""):
                        restrictions.append(f"{k}: {v}")
                _walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for item in obj:
                _walk(item, path)

    _walk(data)
    return {"restrictions": restrictions, "wanted": wanted}


async def car_check(plate: str) -> dict:
    """
    Проверяет автомобиль по госномеру через ГИБДД и ЕАИСТО.

    Возвращает:
      {
        "plate": "<нормализованный номер>",
        "restrictions": [...],
        "wanted": True/False,
        "eaisto": {...} | None,
        "gibdd_raw": {...} | None,
      }
      или {"error": "..."}
    """
    plate_norm = normalize_plate(plate)
    log.debug("car_check: проверка номера %r", plate_norm)

    gibdd_result = None
    eaisto_result = None

    headers_gibdd = {
        **_HEADERS,
        "Referer": "https://xn--90adear.xn--p1ai/check/auto",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        # — ГИБДД check/auto —
        try:
            log.debug("car_check: POST %s  plateId=%r", _GIBDD_URL, plate_norm)
            resp = await client.post(
                _GIBDD_URL,
                data={
                    "plateId": plate_norm,
                    "checkType": "auto",
                    "regionId": "",
                },
                headers=headers_gibdd,
            )
            log.debug("car_check: ГИБДД HTTP %d", resp.status_code)

            if resp.status_code == 200:
                try:
                    gibdd_result = resp.json()
                    log.debug("car_check: ГИБДД ответ получен, ключи: %s", list(gibdd_result.keys()) if isinstance(gibdd_result, dict) else type(gibdd_result))
                except Exception as je:
                    log.error("car_check: ГИБДД JSON parse error %s; тело: %s", je, resp.text[:200])
                    # Проверяем на CAPTCHA
                    if "captcha" in resp.text.lower():
                        log.debug("car_check: ГИБДД вернул CAPTCHA")
                        gibdd_result = {"_captcha": True}
            else:
                log.error("car_check: ГИБДД вернул HTTP %d", resp.status_code)

        except httpx.RequestError as exc:
            log.error("car_check: ГИБДД сетевая ошибка %s", exc)

        # — ЕАИСТО —
        try:
            log.debug("car_check: POST %s  plateId=%r", _EAISTO_URL, plate_norm)
            resp2 = await client.post(
                _EAISTO_URL,
                data={
                    "plateId": plate_norm,
                    "checkType": "EAISTO",
                },
                headers={
                    **_HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://eaisto.gibdd.ru/",
                },
            )
            log.debug("car_check: ЕАИСТО HTTP %d", resp2.status_code)

            if resp2.status_code == 200:
                try:
                    eaisto_result = resp2.json()
                    log.debug("car_check: ЕАИСТО ответ, ключи: %s", list(eaisto_result.keys()) if isinstance(eaisto_result, dict) else type(eaisto_result))
                except Exception as je:
                    log.error("car_check: ЕАИСТО JSON parse error %s", je)
            else:
                log.error("car_check: ЕАИСТО вернул HTTP %d", resp2.status_code)

        except httpx.RequestError as exc:
            log.error("car_check: ЕАИСТО сетевая ошибка %s", exc)

    # Если ничего не получили
    if gibdd_result is None and eaisto_result is None:
        return {"error": "Не удалось получить данные от ГИБДД и ЕАИСТО"}

    # Разбираем результат ГИБДД
    restrictions: list[str] = []
    wanted = False

    if isinstance(gibdd_result, dict) and not gibdd_result.get("_captcha"):
        parsed = _parse_gibdd_response(gibdd_result)
        restrictions = parsed["restrictions"]
        wanted = parsed["wanted"]
        log.debug("car_check: ограничений %d, розыск=%s", len(restrictions), wanted)
    elif isinstance(gibdd_result, dict) and gibdd_result.get("_captcha"):
        log.debug("car_check: ГИБДД недоступен (CAPTCHA)")

    return {
        "plate": plate_norm,
        "restrictions": restrictions,
        "wanted": wanted,
        "eaisto": eaisto_result,
        "gibdd_raw": gibdd_result if not (isinstance(gibdd_result, dict) and gibdd_result.get("_captcha")) else None,
        "gibdd_captcha": isinstance(gibdd_result, dict) and gibdd_result.get("_captcha", False),
    }
