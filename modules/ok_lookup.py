import logging
import re
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}

OK_API = "https://api.ok.ru/fb.do"


async def ok_user_lookup(query: str) -> dict:
    """Поиск публичного профиля OK.ru по username или числовому ID."""
    query = query.strip().lstrip("@")
    log.debug("ok_user_lookup: запрос %r", query)

    result: dict = {}

    # --- попытка через официальный публичный API (без ключа, только для числовых uid) ---
    if query.isdigit():
        api_data = await _api_lookup(query)
        if api_data and "error" not in api_data:
            result.update(api_data)
            log.debug("ok_user_lookup: API вернул данные для uid=%s", query)

    # --- скрапинг публичной страницы ---
    url = f"https://ok.ru/{query}"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            r = await client.get(url)
            log.debug("ok_user_lookup: GET %s → %d", url, r.status_code)
            if r.status_code != 200:
                if not result:
                    return {"error": f"HTTP {r.status_code}"}
                result.setdefault("url", url)
                return result
            html = r.text

            # og:title — имя
            m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
            if m:
                result["name"] = m.group(1).strip()
                log.debug("ok_user_lookup: og:title=%r", result["name"])

            # og:description — краткое описание / bio
            m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html)
            if m:
                result["bio"] = m.group(1).strip()[:300]

            # og:image — фото
            m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html)
            if m:
                result["photo"] = m.group(1)

            # Подписчики — разные варианты верстки
            for pattern in [
                r'(\d[\d\s]*)\s*подписчик',
                r'"subscribersCount"\s*:\s*(\d+)',
                r'data-count=["\'](\d+)["\'][^>]*>.*?подписчик',
            ]:
                m = re.search(pattern, html, re.I)
                if m:
                    raw = re.sub(r'\s', '', m.group(1))
                    if raw.isdigit():
                        result["followers"] = int(raw)
                        break

            # Город/местоположение
            m = re.search(r'"location"\s*:\s*"([^"]+)"', html)
            if not m:
                m = re.search(r'city["\s:]+([А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\s\-]+)', html)
            if m:
                result["location"] = m.group(1).strip()[:100]

    except httpx.RequestError as exc:
        log.error("ok_user_lookup: ошибка сети %s", exc)
        if not result:
            return {"error": f"Ошибка сети: {exc}"}

    if not result.get("name"):
        if not result:
            return {"error": "Профиль не найден или закрыт"}
        result.setdefault("name", query)

    result["url"] = f"https://ok.ru/{query}"
    log.debug("ok_user_lookup: итог %r", result)
    return result


async def _api_lookup(uid: str) -> dict:
    """Публичный API OK без ключа (работает только для числовых uid)."""
    params = {
        "method": "users.getInfo",
        "uids": uid,
        "fields": "name,pic_full,location,followers_count",
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS) as client:
            r = await client.get(OK_API, params=params)
            if r.status_code != 200:
                log.debug("ok _api_lookup: HTTP %d", r.status_code)
                return {}
            data = r.json()
            if isinstance(data, list) and data:
                u = data[0]
                return {
                    "name": u.get("name"),
                    "photo": u.get("pic_full"),
                    "location": u.get("location", {}).get("city") if isinstance(u.get("location"), dict) else None,
                    "followers": u.get("followers_count"),
                }
    except Exception as exc:
        log.debug("ok _api_lookup: исключение %s", exc)
    return {}
