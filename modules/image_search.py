import asyncio
import httpx
import re
from config import REQUEST_TIMEOUT

YANDEX_SEARCH = "https://yandex.ru/images/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


async def reverse_image_yandex(image_bytes: bytes, filename: str = "photo.jpg") -> dict:
    """Загружает фото в Yandex Images и возвращает результаты поиска."""
    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as client:
            # Шаг 1: загружаем изображение
            upload_r = await client.post(
                "https://yandex.ru/images-apphost/image-download",
                files={"upfile": (filename, image_bytes, "image/jpeg")},
                params={"url": "", "recent": "1"},
                headers={**HEADERS, "Referer": "https://yandex.ru/images/"},
            )
            if upload_r.status_code != 200:
                return {"error": f"Yandex upload failed: {upload_r.status_code}"}

            cbir_id = upload_r.json().get("blocks", [{}])[0].get("params", {}).get("url", "")
            if not cbir_id:
                # Пробуем альтернативный путь
                raw = upload_r.text
                m = re.search(r'"cbir_id":"([^"]+)"', raw)
                cbir_id = m.group(1) if m else ""

            if not cbir_id:
                return {"error": "Не удалось получить cbir_id"}

            # Шаг 2: получаем результаты поиска
            search_r = await client.get(
                YANDEX_SEARCH,
                params={"cbir_id": cbir_id, "rpt": "imageview", "source": "qa"},
                headers={**HEADERS, "Referer": "https://yandex.ru/images/"},
            )
            html = search_r.text

            results = _parse_yandex_results(html)
            similar_sites = _extract_similar_sites(html)

            return {
                "cbir_id": cbir_id,
                "search_url": f"https://yandex.ru/images/search?cbir_id={cbir_id}&rpt=imageview",
                "results": results[:10],
                "similar_sites": similar_sites[:10],
            }

    except Exception as e:
        return {"error": str(e)}


def _parse_yandex_results(html: str) -> list[dict]:
    results = []
    # Парсим сниппеты из JSON в HTML (Yandex встраивает данные в JS)
    pattern = re.compile(r'"snippet":\{"title":"([^"]+)","text":"([^"]*)".*?"url":"([^"]+)"', re.S)
    for m in pattern.finditer(html):
        results.append({
            "title": m.group(1),
            "text": m.group(2),
            "url": m.group(3),
        })
    return results


def _extract_similar_sites(html: str) -> list[str]:
    # Вытаскиваем домены из результатов
    urls = re.findall(r'https?://([a-zA-Z0-9.-]+)', html)
    seen = set()
    result = []
    for u in urls:
        if u not in seen and "yandex" not in u and len(u) > 4:
            seen.add(u)
            result.append(u)
    return result
