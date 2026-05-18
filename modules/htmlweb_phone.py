"""
htmlweb.ru — бесплатный пробив телефона без ключа.
Возвращает оператора, регион, код страны.
"""
import logging
import re
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)


async def htmlweb_phone(phone: str) -> dict:
    """
    Пробивает номер через htmlweb.ru.
    phone — в любом формате, очищается автоматически.
    """
    clean = re.sub(r"[^\d]", "", phone)
    if clean.startswith("8") and len(clean) == 11:
        clean = "7" + clean[1:]
    log.debug("htmlweb_phone: %r → %r", phone, clean)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                "https://htmlweb.ru/geo/api.php",
                params={"json": 1, "telcod": clean},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            log.debug("htmlweb_phone: HTTP %d", r.status_code)
            if r.status_code != 200:
                return {"error": f"htmlweb HTTP {r.status_code}"}
            d = r.json()
            if "error" in d:
                return {"error": d["error"]}

            country = d.get("country", {})
            capital = d.get("capital", {})
            operator = d.get("0", {}).get("oper", "")

            return {
                "phone":       clean,
                "country":     country.get("russian", country.get("english", "")),
                "country_code": country.get("id", ""),
                "region":      country.get("location", ""),
                "city":        capital.get("russian", capital.get("english", "")),
                "operator":    operator,
                "timezone":    capital.get("timezone", ""),
                "lat":         capital.get("latitude", ""),
                "lon":         capital.get("longitude", ""),
            }
    except Exception as e:
        log.error("htmlweb_phone: %s", e)
        return {"error": str(e)}


async def whatsapp_check(phone: str) -> dict:
    """
    Проверяет наличие WhatsApp по номеру.
    Возвращает ссылку для быстрого открытия чата.
    """
    clean = re.sub(r"[^\d]", "", phone)
    if clean.startswith("8") and len(clean) == 11:
        clean = "7" + clean[1:]
    log.debug("whatsapp_check: %r", clean)
    wa_link = f"https://wa.me/{clean}"
    wa_api  = f"https://api.whatsapp.com/send?phone={clean}"
    try:
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            r = await client.get(wa_api)
            # WhatsApp всегда возвращает 200, ищем маркеры в теле
            registered = (
                '"has_wa":true' in r.text or
                '"number_exists":true' in r.text or
                "open.whatsapp.com" in r.text.lower() or
                "waweb" in r.text.lower()
            )
            return {
                "phone":      clean,
                "wa_link":    wa_link,
                "registered": registered,
                "status":     r.status_code,
            }
    except Exception as e:
        log.error("whatsapp_check: %s", e)
        return {"phone": clean, "wa_link": wa_link, "registered": None, "error": str(e)}
