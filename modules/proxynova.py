"""
Proxynova COMB — поиск по Collection of Many Breaches (3.2 млрд записей).
Бесплатно, без ключа. Поддерживает: email, username, имя.
Docs: https://api.proxynova.com
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

PROXYNOVA_API = "https://api.proxynova.com/comb"


async def proxynova_search(query: str, limit: int = 20) -> dict:
    """
    Ищет query в COMB-базе. Возвращает список строк формата login:password.
    """
    log.debug("proxynova_search: %r", query)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                PROXYNOVA_API,
                params={"query": query},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            log.debug("proxynova_search: HTTP %d", r.status_code)
            if r.status_code != 200:
                return {"error": f"Proxynova HTTP {r.status_code}"}

            data = r.json()
            count = data.get("count", 0)
            all_lines = data.get("lines", [])

            # Фильтруем точные совпадения — строка должна начинаться с query
            q_lower = query.lower()
            exact_lines = [l for l in all_lines if l.lower().startswith(q_lower + ":") or l.lower() == q_lower]

            # Если нет точных — берём все (для username/имён)
            lines = exact_lines if exact_lines else []
            exact_count = len(exact_lines)

            log.debug("proxynova_search: всего=%d точных=%d", count, exact_count)

            results = []
            for line in lines[:limit]:
                if ":" in line:
                    parts = line.split(":", 1)
                    results.append({"login": parts[0], "password": parts[1]})
                else:
                    results.append({"login": line, "password": ""})

            return {"found": exact_count, "total_fuzzy": count, "results": results}

    except Exception as e:
        log.error("proxynova_search: %s", e)
        return {"error": str(e)}
