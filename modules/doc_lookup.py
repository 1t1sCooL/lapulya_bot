"""
Проверка документов через публичные сервисы:
  - Паспорт РФ  (МВД / Сервис проверки документов)
  - ИНН физлица по ФИО + дата рождения (ФНС service.nalog.ru)
  - Валидация ИНН алгоритмом контрольной суммы (без API)
"""
import logging
import re

import httpx

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

_PASSPORT_URL = "https://xn--b1afk4ae.xn--b1agbmb2a.xn--p1ai/info-service.htm"   # гувм.мвд.рф
_INN_URL = "https://service.nalog.ru/inn-by-code.do"


# ---------------------------------------------------------------------------
# Паспорт
# ---------------------------------------------------------------------------

async def _get_passport_csrf(client: httpx.AsyncClient) -> tuple[str, str]:
    """
    Делает GET на страницу сервиса МВД и извлекает CSRF-токен и session cookie.
    Возвращает (csrf_token, cookie_header).
    """
    log.debug("passport: GET %s?sid=2000", _PASSPORT_URL)
    resp = await client.get(
        _PASSPORT_URL,
        params={"sid": "2000"},
        headers=_HEADERS,
        follow_redirects=True,
    )
    log.debug("passport: CSRF страница HTTP %d", resp.status_code)
    resp.raise_for_status()

    html = resp.text
    # Ищем CSRF-токен в различных форматах
    csrf = ""
    patterns = [
        r'name="_csrf"[^>]+value="([^"]+)"',
        r'name="csrf"[^>]+value="([^"]+)"',
        r'"_csrf"\s*:\s*"([^"]+)"',
        r'csrfToken\s*=\s*["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']_csrf["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            csrf = m.group(1)
            log.debug("passport: CSRF найден: %r", csrf)
            break

    if not csrf:
        log.debug("passport: CSRF не найден в HTML (длина: %d)", len(html))

    return csrf, ""


async def check_passport(series: str, number: str) -> dict:
    """
    Проверяет действительность паспорта РФ через сервис МВД.

    Args:
        series: серия из 4 цифр (например, "4510")
        number: номер из 6 цифр (например, "123456")

    Возвращает:
        {"valid": True/False/None, "status": "действителен/недействителен/сервис недоступен"}
    """
    series = series.strip().replace(" ", "")
    number = number.strip().replace(" ", "")

    log.debug("check_passport: серия=%r номер=%r", series, number)

    # Базовая валидация формата
    if not re.fullmatch(r"\d{4}", series):
        return {"valid": None, "status": "Неверный формат серии (4 цифры)"}
    if not re.fullmatch(r"\d{6}", number):
        return {"valid": None, "status": "Неверный формат номера (6 цифр)"}

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        # Шаг 1 — получить страницу и CSRF
        csrf = ""
        try:
            csrf, _ = await _get_passport_csrf(client)
        except Exception as exc:
            log.error("check_passport: не удалось получить CSRF: %s", exc)

        # Шаг 2 — отправить запрос
        series_number = f"{series} {number}"
        payload: dict = {
            "seriesAndNumber": series_number,
        }
        if csrf:
            payload["_csrf"] = csrf

        headers_post = {
            **_HEADERS,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{_PASSPORT_URL}?sid=2000",
            "Origin": "https://xn--b1afk4ae.xn--b1agbmb2a.xn--p1ai",
        }

        log.debug("check_passport: POST %s  payload keys: %s", _PASSPORT_URL, list(payload.keys()))

        try:
            resp = await client.post(
                _PASSPORT_URL,
                params={"sid": "2000"},
                data=payload,
                headers=headers_post,
            )
            log.debug("check_passport: HTTP %d", resp.status_code)

            if resp.status_code != 200:
                log.error("check_passport: HTTP %d", resp.status_code)
                return {"valid": None, "status": "Сервис МВД недоступен"}

            body = resp.text.lower()
            log.debug("check_passport: тело ответа (первые 500 символов): %s", resp.text[:500])

            if "действительный" in body or "паспорт действителен" in body or "is valid" in body:
                return {"valid": True, "status": "действителен"}
            elif "недействительный" in body or "паспорт недействителен" in body or "not valid" in body or "is invalid" in body:
                return {"valid": False, "status": "недействителен"}
            elif "captcha" in body or "капча" in body:
                log.debug("check_passport: сервис требует CAPTCHA")
                return {"valid": None, "status": "Сервис требует CAPTCHA — попробуйте позже"}
            else:
                log.debug("check_passport: статус не распознан в ответе")
                return {"valid": None, "status": "Не удалось определить статус (сервис изменился)"}

        except httpx.RequestError as exc:
            log.error("check_passport: сетевая ошибка %s", exc)
            return {"valid": None, "status": "Сетевая ошибка — сервис МВД недоступен"}
        except Exception as exc:
            log.error("check_passport: неожиданная ошибка %s", exc)
            return {"valid": None, "status": f"Ошибка: {exc}"}


# ---------------------------------------------------------------------------
# ИНН по ФИО
# ---------------------------------------------------------------------------

async def find_inn(last: str, first: str, middle: str, birthdate: str) -> dict:
    """
    Ищет ИНН физлица по ФИО и дате рождения через ФНС.

    Args:
        last:      фамилия
        first:     имя
        middle:    отчество (можно пустую строку)
        birthdate: дата рождения в формате дд.мм.гггг

    Возвращает:
        {"inn": "..."} или {"error": "..."}
    """
    last = last.strip()
    first = first.strip()
    middle = middle.strip()
    birthdate = birthdate.strip()

    log.debug("find_inn: %s %s %s, дата=%r", last, first, middle, birthdate)

    # Валидация даты
    if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", birthdate):
        return {"error": "Неверный формат даты (дд.мм.гггг)"}

    payload = {
        "fam": last,
        "nam": first,
        "otch": middle,
        "bdate": birthdate,
        "bplace": "",
        "doctype": "21",
        "docno": "",
        "docdt": "",
        "c": "innMy",
        "ifns": "",
    }

    headers = {
        **_HEADERS,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://service.nalog.ru/inn.do",
        "Origin": "https://service.nalog.ru",
    }

    log.debug("find_inn: POST %s", _INN_URL)

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.post(_INN_URL, data=payload, headers=headers)
            log.debug("find_inn: HTTP %d", resp.status_code)
            resp.raise_for_status()

            data = resp.json()
            log.debug("find_inn: ответ %s", data)

            inn = data.get("inn") or data.get("code")
            if inn:
                log.debug("find_inn: найден ИНН %r", inn)
                return {"inn": str(inn)}

            error = data.get("error") or data.get("message") or data.get("errorMessage")
            if error:
                log.debug("find_inn: сервис вернул ошибку %r", error)
                return {"error": str(error)}

            # Если ИНН пуст — не найден
            log.debug("find_inn: ИНН не найден, ответ: %s", data)
            return {"error": "ИНН не найден по указанным данным"}

    except httpx.HTTPStatusError as exc:
        log.error("find_inn: HTTP ошибка %s", exc)
        return {"error": f"HTTP {exc.response.status_code} от ФНС"}
    except httpx.RequestError as exc:
        log.error("find_inn: сетевая ошибка %s", exc)
        return {"error": "Сетевая ошибка при обращении к ФНС"}
    except Exception as exc:
        log.error("find_inn: неожиданная ошибка %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Валидация ИНН (алгоритм, без API)
# ---------------------------------------------------------------------------

def _inn_checksum(digits: list[int], weights: list[int]) -> int:
    return sum(d * w for d, w in zip(digits, weights)) % 11 % 10


def validate_inn(inn: str) -> bool:
    """
    Проверяет контрольную сумму ИНН (10-значный ЮЛ или 12-значный ФЛ).
    Возвращает True если ИНН корректный, иначе False.
    """
    inn = inn.strip()
    if not inn.isdigit():
        log.debug("validate_inn: %r содержит нецифровые символы", inn)
        return False

    length = len(inn)
    digits = [int(c) for c in inn]

    if length == 10:
        # ЮЛ: один контрольный разряд
        w = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        ctrl = _inn_checksum(digits[:9], w)
        valid = ctrl == digits[9]
        log.debug("validate_inn[10]: %r → %s", inn, valid)
        return valid

    elif length == 12:
        # ФЛ: два контрольных разряда
        w1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        w2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        ctrl1 = _inn_checksum(digits[:10], w1)
        ctrl2 = _inn_checksum(digits[:11], w2)
        valid = ctrl1 == digits[10] and ctrl2 == digits[11]
        log.debug("validate_inn[12]: %r → %s", inn, valid)
        return valid

    else:
        log.debug("validate_inn: неверная длина %d для %r", length, inn)
        return False
