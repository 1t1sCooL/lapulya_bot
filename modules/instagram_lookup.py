import json
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
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def instagram_lookup(username: str) -> dict:
    """Получает публичный профиль Instagram без авторизации."""
    username = username.strip().lstrip("@")
    log.debug("instagram_lookup: запрос %r", username)

    result: dict = {"username": username, "url": f"https://www.instagram.com/{username}/"}

    # --- попытка 1: ?__a=1&__d=dis JSON endpoint ---
    json_data = await _try_json_endpoint(username)
    if json_data and "error" not in json_data:
        result.update(json_data)
        log.debug("instagram_lookup: JSON endpoint сработал для %r", username)
        return result

    # --- попытка 2: скрапинг HTML + ld+json / window._sharedData ---
    html_data = await _try_html_scrape(username)
    if html_data:
        result.update(html_data)
        log.debug("instagram_lookup: HTML scrape сработал для %r", username)
        return result

    log.warning("instagram_lookup: все методы не дали результата для %r", username)
    return {"error": "Профиль не найден или закрыт", "username": username, "url": result["url"]}


async def _try_json_endpoint(username: str) -> dict:
    url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            r = await client.get(url)
            log.debug("instagram _try_json_endpoint: %s → %d", url, r.status_code)
            if r.status_code != 200:
                return {}
            data = r.json()
            user = (
                data.get("graphql", {}).get("user")
                or data.get("data", {}).get("user")
                or {}
            )
            if not user:
                return {}
            return _parse_user_obj(user)
    except Exception as exc:
        log.debug("instagram _try_json_endpoint: исключение %s", exc)
        return {}


async def _try_html_scrape(username: str) -> dict:
    url = f"https://www.instagram.com/{username}/"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            r = await client.get(url)
            log.debug("instagram _try_html_scrape: %s → %d", url, r.status_code)
            if r.status_code != 200:
                return {}
            html = r.text

            # window._sharedData
            m = re.search(r'window\._sharedData\s*=\s*(\{.*?\});\s*</script>', html, re.S)
            if m:
                try:
                    shared = json.loads(m.group(1))
                    user = (
                        shared.get("entry_data", {})
                              .get("ProfilePage", [{}])[0]
                              .get("graphql", {})
                              .get("user", {})
                    )
                    if user:
                        log.debug("instagram: нашли _sharedData для %r", username)
                        return _parse_user_obj(user)
                except (json.JSONDecodeError, IndexError, KeyError) as exc:
                    log.debug("instagram _sharedData parse error: %s", exc)

            # application/ld+json
            m = re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
            if m:
                try:
                    ld = json.loads(m.group(1))
                    if isinstance(ld, list):
                        ld = ld[0] if ld else {}
                    result: dict = {}
                    if ld.get("name"):
                        result["full_name"] = ld["name"]
                    if ld.get("description"):
                        result["bio"] = ld["description"][:300]
                    if ld.get("interactionStatistic"):
                        for stat in ld["interactionStatistic"]:
                            itype = stat.get("interactionType", "")
                            count = stat.get("userInteractionCount", 0)
                            if "Follow" in itype:
                                result["followers"] = count
                    if result:
                        log.debug("instagram: нашли ld+json для %r", username)
                        return result
                except (json.JSONDecodeError, KeyError) as exc:
                    log.debug("instagram ld+json parse error: %s", exc)

            # meta og-tags fallback
            result = {}
            m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
            if m:
                result["full_name"] = m.group(1).replace(" • Instagram", "").strip()
            m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html)
            if m:
                result["bio"] = m.group(1)[:300]
            for pattern in [r'(\d[\d,\.]+)\s*[Ff]ollowers', r'(\d[\d,\.]+)\s*подписчик']:
                m = re.search(pattern, html)
                if m:
                    result["followers"] = _parse_count(m.group(1))
                    break
            if result.get("full_name"):
                return result

    except Exception as exc:
        log.error("instagram _try_html_scrape: исключение %s", exc)
    return {}


def _parse_user_obj(user: dict) -> dict:
    """Извлекает поля из graphql user object."""
    followers = 0
    edge_followers = user.get("edge_followed_by") or {}
    if isinstance(edge_followers, dict):
        followers = edge_followers.get("count", 0)

    following = 0
    edge_following = user.get("edge_follow") or {}
    if isinstance(edge_following, dict):
        following = edge_following.get("count", 0)

    posts = 0
    edge_media = user.get("edge_owner_to_timeline_media") or {}
    if isinstance(edge_media, dict):
        posts = edge_media.get("count", 0)

    return {
        "full_name": user.get("full_name"),
        "bio": (user.get("biography") or "")[:300] or None,
        "followers": followers or None,
        "following": following or None,
        "posts": posts or None,
        "verified": user.get("is_verified", False),
        "private": user.get("is_private", False),
        "external_url": user.get("external_url"),
    }


def _parse_count(raw: str) -> int:
    raw = raw.replace(",", "").replace(".", "").strip()
    try:
        return int(raw)
    except ValueError:
        return 0
