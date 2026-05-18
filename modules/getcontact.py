"""
GetContact — неофициальный API для поиска имени по номеру телефона.
Требует токен аккаунта из мобильного приложения GetContact.

Как получить токен:
1. Установи GetContact на телефон и зарегистрируйся
2. Перехвати трафик (Charles Proxy / mitmproxy) — ищи заголовок Authorization: Bearer <token>
   ИЛИ используй эмулятор Android + Frida для извлечения токена
3. Сохрани токен в GETCONTACT_TOKEN в .env
"""
import logging
import hashlib
import time
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

GETCONTACT_API = "https://api.getcontact.com/v1"


def _gc_headers(token: str) -> dict:
    ts = str(int(time.time()))
    return {
        "Authorization": f"Bearer {token}",
        "X-App-Version": "6.1.1",
        "X-Os": "android",
        "X-Timestamp": ts,
        "X-Token": token,
        "Content-Type": "application/json",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11)",
        "Accept-Language": "ru",
    }


async def getcontact_search(phone: str, token: str) -> dict:
    """
    Ищет имя владельца номера через GetContact.
    phone: номер в E.164 формате (+79001234567)
    Возвращает {"name": "...", "tags": [...]} или {"error": "..."}
    """
    if not token:
        return {"error": "GETCONTACT_TOKEN не задан"}

    log.debug("getcontact_search: запрос %r", phone)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.post(
                f"{GETCONTACT_API}/search/phone",
                json={"phone": phone},
                headers=_gc_headers(token),
            )
            log.debug("getcontact_search: HTTP %d", r.status_code)
            if r.status_code == 401:
                return {"error": "GetContact: токен истёк или неверный"}
            if r.status_code == 429:
                return {"error": "GetContact: rate limit"}
            if r.status_code != 200:
                return {"error": f"GetContact: HTTP {r.status_code}"}

            data = r.json()
            profile = data.get("data", {}).get("profile", {})
            tags = data.get("data", {}).get("tags", [])

            name = profile.get("name", "")
            log.debug("getcontact_search: имя=%r тегов=%d", name, len(tags))
            return {
                "name": name,
                "tags": [t.get("tag", "") for t in tags[:10]],
                "raw": profile,
            }
    except Exception as e:
        log.error("getcontact_search: ошибка %s", e)
        return {"error": str(e)}
