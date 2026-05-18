"""
ЕГРЮЛ/ЕГРИП — поиск ЮЛ/ИП по ИНН, ОГРН или наименованию
через публичный API ФНС egrul.nalog.ru (без ключа).
"""
import logging

import httpx

log = logging.getLogger(__name__)

_BASE = "https://egrul.nalog.ru"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://egrul.nalog.ru/",
}

# Таблица кириллических аналогов — ФНС иногда отдаёт статусы латиницей
_KIND_MAP = {
    "Ю": "ЮЛ",
    "П": "ИП",
}


async def egrul_search(query: str) -> dict:
    """
    Ищет организации/ИП по ИНН, ОГРН или наименованию.

    Алгоритм:
      1. POST /  — получить токен
      2. GET /search-result/<token>  — получить строки

    Возвращает:
      {"results": [{"name","inn","ogrn","address","status","kind"}], "found": N}
      или {"error": "..."}
    """
    query = query.strip()
    log.debug("egrul_search: запрос %r", query)

    try:
        async with httpx.AsyncClient(
            headers=_HEADERS, timeout=20, follow_redirects=True
        ) as client:
            # Шаг 1 — получить токен
            log.debug("egrul_search: POST %s/  query=%r", _BASE, query)
            resp1 = await client.post(
                f"{_BASE}/",
                data={
                    "query": query,
                    "region": "",
                    "PreventChromeAutocomplete": "",
                },
                headers={**_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
            )
            log.debug("egrul_search: токен HTTP %d", resp1.status_code)
            resp1.raise_for_status()

            token_data = resp1.json()
            token = token_data.get("t")
            if not token:
                log.error("egrul_search: токен не получен, ответ: %s", token_data)
                return {"error": "Не удалось получить токен от ФНС"}

            log.debug("egrul_search: токен получен %r", token)

            # Шаг 2 — получить результаты
            log.debug("egrul_search: GET %s/search-result/%s", _BASE, token)
            resp2 = await client.get(f"{_BASE}/search-result/{token}")
            log.debug("egrul_search: результаты HTTP %d", resp2.status_code)
            resp2.raise_for_status()

            data = resp2.json()

    except httpx.HTTPStatusError as exc:
        log.error("egrul_search: HTTP ошибка %s", exc)
        return {"error": f"HTTP {exc.response.status_code} от ФНС"}
    except httpx.RequestError as exc:
        log.error("egrul_search: сетевая ошибка %s", exc)
        return {"error": "Сетевая ошибка при обращении к ФНС"}
    except Exception as exc:
        log.error("egrul_search: неожиданная ошибка %s", exc)
        return {"error": str(exc)}

    rows = data.get("rows", [])
    log.debug("egrul_search: получено строк %d", len(rows))

    if not rows:
        return {"results": [], "found": 0}

    results = []
    for row in rows:
        name = row.get("n") or row.get("c") or ""
        short_name = row.get("c") or ""
        inn = row.get("g") or ""
        ogrn = row.get("o") or ""
        address = row.get("a") or ""
        status = row.get("r") or ""
        kind_raw = row.get("k") or ""
        kind = _KIND_MAP.get(kind_raw, kind_raw or "—")

        results.append(
            {
                "name": name,
                "short_name": short_name,
                "inn": inn,
                "ogrn": ogrn,
                "address": address,
                "status": status,
                "kind": kind,
            }
        )

    log.debug("egrul_search: обработано %d записей", len(results))
    return {"results": results, "found": len(results)}
