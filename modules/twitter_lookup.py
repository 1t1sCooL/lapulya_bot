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
    "Accept-Language": "en-US,en;q=0.9",
}

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]


async def twitter_lookup(username: str) -> dict:
    """Получает публичный профиль Twitter/X через nitter или прямой скрапинг x.com."""
    username = username.strip().lstrip("@")
    log.debug("twitter_lookup: запрос %r", username)

    # --- пробуем каждый nitter-инстанс ---
    for instance in NITTER_INSTANCES:
        url = f"{instance}/{username}"
        data = await _scrape_nitter(url, username, instance)
        if data and "error" not in data:
            log.debug("twitter_lookup: нашли через %s", instance)
            return data
        log.debug("twitter_lookup: %s не ответил / не дал данных", instance)

    # --- fallback: x.com meta-теги ---
    log.debug("twitter_lookup: fallback → x.com для %r", username)
    data = await _scrape_xcom(username)
    if data and "error" not in data:
        return data

    return {
        "error": "Профиль не найден. Nitter недоступен, x.com отдаёт только JS-оболочку.",
        "username": username,
        "url": f"https://x.com/{username}",
    }


async def _scrape_nitter(url: str, username: str, instance: str) -> dict:
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            log.debug("nitter GET %s → %d", url, r.status_code)
            if r.status_code != 200:
                return {}
            html = r.text

            # Проверяем, что это реальная страница профиля
            if "user not found" in html.lower() or "этот пользователь" in html.lower():
                return {}

            result: dict = {
                "username": username,
                "url": f"https://x.com/{username}",
                "source": instance,
            }

            # Отображаемое имя
            m = re.search(r'<a class="profile-card-fullname"[^>]*>\s*(.*?)\s*</a>', html, re.S)
            if not m:
                m = re.search(r'<title>\s*(.*?)\s*\(', html)
            if m:
                result["name"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()

            # Bio
            m = re.search(r'<div class="profile-bio"[^>]*>\s*<p[^>]*>(.*?)</p>', html, re.S)
            if m:
                result["bio"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()[:300]

            # Счётчики: нитер показывает их в .profile-stat-num
            nums = re.findall(r'<span class="profile-stat-num"[^>]*>([\d,\.KkMm]+)</span>', html)
            labels = re.findall(r'<span class="profile-stat-header"[^>]*>(.*?)</span>', html)
            for label, num in zip(labels, nums):
                label_clean = label.strip().lower()
                num_clean = _parse_nitter_count(num)
                if "tweet" in label_clean or "post" in label_clean:
                    result["tweets"] = num_clean
                elif "follow" in label_clean and "ing" in label_clean:
                    result["following"] = num_clean
                elif "follow" in label_clean:
                    result["followers"] = num_clean

            # Дата регистрации
            m = re.search(r'<span[^>]*title="([^"]*)"[^>]*>\s*(?:Joined|Зарегистрирован)\s*</span>', html)
            if not m:
                m = re.search(r'Joined\s+<span[^>]*title="([^"]+)"', html)
            if m:
                result["joined"] = m.group(1).strip()

            # Верификация
            result["verified"] = bool(
                re.search(r'class="[^"]*verified[^"]*"', html)
                or re.search(r'verified-icon', html)
            )

            if result.get("name"):
                return result
    except httpx.RequestError as exc:
        log.debug("nitter %s: ошибка сети %s", url, exc)
    except Exception as exc:
        log.error("nitter %s: неожиданная ошибка %s", url, exc)
    return {}


async def _scrape_xcom(username: str) -> dict:
    """Парсит мета-теги страницы x.com (работает частично, т.к. x.com — SPA)."""
    url = f"https://x.com/{username}"
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            log.debug("x.com GET %s → %d", url, r.status_code)
            if r.status_code != 200:
                return {}
            html = r.text
            result: dict = {"username": username, "url": url}

            m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
            if m:
                result["name"] = m.group(1).replace(" / X", "").replace(" on X", "").strip()

            m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html)
            if m:
                result["bio"] = m.group(1)[:300]

            m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', html)
            if m and not result.get("bio"):
                result["bio"] = m.group(1)[:300]

            if result.get("name"):
                return result
    except httpx.RequestError as exc:
        log.debug("x.com scrape: ошибка сети %s", exc)
    except Exception as exc:
        log.error("x.com scrape: неожиданная ошибка %s", exc)
    return {}


def _parse_nitter_count(raw: str) -> int:
    """Конвертирует '1.2K', '3M', '4,567' в int."""
    raw = raw.strip().replace(",", "")
    try:
        if raw.upper().endswith("K"):
            return int(float(raw[:-1]) * 1_000)
        if raw.upper().endswith("M"):
            return int(float(raw[:-1]) * 1_000_000)
        return int(raw)
    except ValueError:
        return 0
