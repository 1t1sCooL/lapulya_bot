"""
Cassandra.sh — поиск по базам утечек, аналог Scylla.sh.
Бесплатно, без ключа.
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)


async def cassandra_search(query: str, size: int = 20) -> dict:
    """
    Поиск по утечкам. Возвращает реальные записи: email, password, username, IP.
    """
    log.debug("cassandra_search: %r", query)
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            r = await client.get(
                "https://cassandra.sh/search",
                params={"q": query, "size": size},
            )
            log.debug("cassandra_search: HTTP %d", r.status_code)
            if r.status_code == 404:
                return {"found": 0, "results": []}
            if r.status_code == 503:
                return {"error": "Cassandra: сервис недоступен"}
            if r.status_code == 429:
                return {"error": "Cassandra: rate limit"}
            if r.status_code != 200:
                return {"error": f"Cassandra: HTTP {r.status_code}"}

            data = r.json()
            if isinstance(data, list):
                hits = data
            elif isinstance(data, dict):
                hits = (data.get("hits") or {}).get("hits") or []
            else:
                hits = []

            results = []
            for hit in hits:
                if not isinstance(hit, dict):
                    continue
                src = hit.get("_source") or {}
                rec = {
                    "email":    src.get("email", ""),
                    "username": src.get("username", ""),
                    "password": src.get("password", ""),
                    "hash":     src.get("hash", ""),
                    "ip":       src.get("ip", ""),
                    "name":     src.get("name", ""),
                    "phone":    src.get("phone", ""),
                    "source":   hit.get("_index", ""),
                }
                if any(v for k, v in rec.items() if k != "source" and v):
                    results.append(rec)

            return {"found": len(results), "results": results}
    except Exception as e:
        log.error("cassandra_search: %s", e)
        return {"error": str(e)}
