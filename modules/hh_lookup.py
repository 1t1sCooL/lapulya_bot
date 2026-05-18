"""
HH.ru (HeadHunter) — поиск публичных резюме по имени.
Открытый API, не требует авторизации для базового поиска.
Docs: https://api.hh.ru/openapi/redoc
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

HH_API = "https://api.hh.ru"
HEADERS = {
    "User-Agent": "osint-bot/1.0 (educational purposes)",
    "HH-User-Agent": "osint-bot/1.0",
}


async def hh_resume_search(name: str, per_page: int = 10) -> dict:
    """
    Ищет публичные резюме по имени через открытый API HH.ru.
    Возвращает {"results": [...], "found": N} или {"error": "..."}.
    """
    log.debug("hh_resume_search: запрос name=%r per_page=%d", name, per_page)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS) as client:
            r = await client.get(
                f"{HH_API}/resumes",
                params={"text": name, "per_page": per_page, "order_by": "relevance"},
            )
            log.debug("hh_resume_search: HTTP %d для %r", r.status_code, name)
            if r.status_code == 403:
                return {"error": "HH.ru: доступ запрещён (требуется авторизация для этого эндпоинта)"}
            if r.status_code != 200:
                return {"error": f"HH.ru HTTP {r.status_code}"}
            data = r.json()
    except httpx.TimeoutException:
        log.error("hh_resume_search: таймаут при запросе %r", name)
        return {"error": "HH.ru: таймаут запроса"}
    except Exception as e:
        log.error("hh_resume_search: ошибка %s", e)
        return {"error": f"HH.ru: {e}"}

    items = data.get("items", [])
    found = data.get("found", len(items))
    log.debug("hh_resume_search: найдено %d резюме (всего на сервере: %d)", len(items), found)

    if not items:
        log.warning("hh_resume_search: 0 результатов для %r", name)

    results = []
    for item in items:
        results.append({
            "title": item.get("title", ""),
            "area": (item.get("area") or {}).get("name", ""),
            "age": item.get("age"),
            "gender": (item.get("gender") or {}).get("name", ""),
            "url": item.get("alternate_url", ""),
            "last_activity": item.get("updated_at", ""),
        })

    return {"results": results, "found": found}
