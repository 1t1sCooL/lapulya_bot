"""
IntelligenceX API — поиск по email, IP, домену, крипто-адресам в дампах, пастах, dark web.
Docs: https://intelx.io/api
Бесплатный tier: 100 запросов/месяц (ограниченные результаты).
"""
import asyncio
import httpx
from config import REQUEST_TIMEOUT

INTELX_API = "https://free.intelx.io"   # free tier URL; paid: https://2.intelx.io


async def intelx_search(query: str, api_key: str, max_results: int = 20) -> dict:
    """Двухэтапный поиск: POST (создать задачу) → GET (забрать результаты)."""
    if not api_key:
        return {"error": "INTELX_API_KEY не задан"}

    headers = {"x-key": api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Шаг 1: запуск поиска
            search_r = await client.post(
                f"{INTELX_API}/intelligent/search",
                headers=headers,
                json={
                    "term": query,
                    "buckets": [],
                    "lookuplevel": 0,
                    "maxresults": max_results,
                    "timeout": 5,
                    "datefrom": "",
                    "dateto": "",
                    "sort": 4,       # по дате (новые сначала)
                    "media": 0,
                    "terminate": [],
                },
            )
            if search_r.status_code != 200:
                return {"error": f"IntelX search failed: HTTP {search_r.status_code}"}

            search_data = search_r.json()
            search_id = search_data.get("id")
            if not search_id:
                return {"error": "IntelX: не получен search_id"}

            # Шаг 2: подождать и забрать результаты
            await asyncio.sleep(2)
            result_r = await client.get(
                f"{INTELX_API}/intelligent/search/result",
                headers=headers,
                params={"id": search_id, "limit": max_results, "offset": 0},
            )
            if result_r.status_code != 200:
                return {"error": f"IntelX result failed: HTTP {result_r.status_code}"}

            result_data = result_r.json()
            records = result_data.get("records") or []

            return {
                "found": len(records),
                "query": query,
                "search_id": search_id,
                "results": [_normalize_intelx(r) for r in records[:30]],
            }

    except Exception as e:
        return {"error": str(e)}


async def intelx_phonebook(query: str, api_key: str, max_results: int = 100) -> dict:
    """
    Phonebook Search — быстрый поиск email/domain/url без полного контента.
    Удобно для поиска всех email на домене или username.
    """
    if not api_key:
        return {"error": "INTELX_API_KEY не задан"}

    headers = {"x-key": api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.post(
                f"{INTELX_API}/phonebook/search",
                headers=headers,
                json={
                    "term": query,
                    "maxresults": max_results,
                    "timeout": 5,
                    "target": 0,   # 0=all, 1=email, 2=domain, 3=url
                    "terminate": [],
                },
            )
            if r.status_code != 200:
                return {"error": f"IntelX phonebook failed: HTTP {r.status_code}"}

            data = r.json()
            search_id = data.get("id")
            if not search_id:
                return {"error": "IntelX phonebook: нет search_id"}

            await asyncio.sleep(1)
            result_r = await client.get(
                f"{INTELX_API}/phonebook/search/result",
                headers=headers,
                params={"id": search_id, "limit": max_results, "offset": 0},
            )
            result_data = result_r.json()
            selectors = result_data.get("selectors") or []

            return {
                "found": len(selectors),
                "query": query,
                "emails": [s["selectorvalue"] for s in selectors if s.get("selectortype") == 1][:50],
                "domains": [s["selectorvalue"] for s in selectors if s.get("selectortype") == 2][:20],
                "urls": [s["selectorvalue"] for s in selectors if s.get("selectortype") == 3][:20],
            }
    except Exception as e:
        return {"error": str(e)}


def _normalize_intelx(rec: dict) -> dict:
    return {
        "name": rec.get("name", ""),
        "date": rec.get("date", "")[:10] if rec.get("date") else "",
        "bucket": rec.get("bucket", ""),
        "media": _media_type(rec.get("media", 0)),
        "size": rec.get("size", 0),
        "storageid": rec.get("storageid", ""),
    }


def _media_type(code: int) -> str:
    types = {
        1: "Pastes", 2: "URLs", 3: "Intelligence Reports",
        4: "Emails", 5: "Documents", 6: "Images",
        7: "Video", 8: "Audio", 9: "Source Code",
        13: "Leaks", 14: "Forums", 19: "Dark Web",
    }
    return types.get(code, f"Media({code})")


async def intelx_file_preview(storage_id: str, api_key: str, lines: int = 10) -> str:
    """
    Читает первые N строк файла из IntelX по storageid.
    Возвращает текст или строку с ошибкой.
    """
    import logging
    log = logging.getLogger(__name__)
    if not api_key:
        return "INTELX_API_KEY не задан"
    log.debug("intelx_file_preview: %r lines=%d", storage_id[:8], lines)
    headers = {"x-key": api_key}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                f"{INTELX_API}/file/preview",
                headers=headers,
                params={"f": 0, "l": lines, "id": storage_id, "k": api_key},
            )
            log.debug("intelx_file_preview: HTTP %d body=%r", r.status_code, r.text[:100])
            if r.status_code in (400, 402, 403, 404):
                return ""   # free tier не поддерживает preview для этого типа
            if r.status_code != 200:
                return ""
            text = r.text.strip()
            return text[:1500] if text else "(пустой файл)"
    except Exception as e:
        log.error("intelx_file_preview: %s", e)
        return f"⚠️ {e}"
