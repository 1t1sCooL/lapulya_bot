import httpx
import re
from config import REQUEST_TIMEOUT

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0)"}


async def tg_user_lookup(username: str) -> dict:
    """Парсит публичную страницу t.me для получения открытых данных."""
    username = username.lstrip("@")
    url = f"https://t.me/{username}"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS) as client:
            r = await client.get(url, follow_redirects=True)
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}
            html = r.text
            result = {"username": username, "url": url}

            # Название
            m = re.search(r'<div class="tgme_page_title"[^>]*>.*?<span[^>]*>(.*?)</span>', html, re.S)
            if m:
                result["name"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()

            # Описание
            m = re.search(r'<div class="tgme_page_description"[^>]*>(.*?)</div>', html, re.S)
            if m:
                result["description"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()[:500]

            # Счётчики (подписчики, участники)
            counters = re.findall(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', html, re.S)
            for c in counters:
                text = re.sub(r"<[^>]+>", "", c).strip()
                if text:
                    result.setdefault("extra", []).append(text)

            # Тип (бот, канал, группа)
            if "tgme_page_action" in html:
                if "Send Message" in html:
                    result["type"] = "Пользователь/Бот"
                elif "View in Telegram" in html:
                    result["type"] = "Канал/Группа"

            # Фото
            m = re.search(r'<img class="tgme_page_photo_img"[^>]*src="([^"]+)"', html)
            if m:
                result["photo"] = m.group(1)

            return result
    except Exception as e:
        return {"error": str(e)}
