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
            lines = data.get("lines", [])[:limit]
            log.debug("proxynova_search: найдено %d записей", count)

            results = []
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 1)
                    results.append({"login": parts[0], "password": parts[1]})
                else:
                    results.append({"login": line, "password": ""})

            return {"found": count, "results": results}

    except Exception as e:
        log.error("proxynova_search: %s", e)
        return {"error": str(e)}
