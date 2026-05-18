"""
Scylla.sh — бесплатный поиск по базам утечек (400M+ записей).
Нет ключа, нет регистрации. Возвращает реальные email/пароль/логин/IP.
Docs: https://scylla.sh
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

SCYLLA_API = "https://scylla.sh"


async def scylla_search(query: str, size: int = 20) -> dict:
    """
    Поиск по Scylla.sh. Возвращает реальные записи из утечек.
    query — email, username, имя, IP и т.д.
    """
    log.debug("scylla_search: %r size=%d", query, size)
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            r = await client.get(
                f"{SCYLLA_API}/search",
                params={"q": query, "size": size},
            )
            log.debug("scylla_search: HTTP %d", r.status_code)
            if r.status_code == 404:
                return {"found": 0, "results": []}
            if r.status_code == 429:
                return {"error": "Scylla: rate limit"}
            if r.status_code == 503:
                return {"error": "Scylla: сервис недоступен"}
            if r.status_code != 200:
                return {"error": f"Scylla: HTTP {r.status_code}"}

            data = r.json()

            # Поддерживаем оба формата: список хитов или ES-объект
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
                # Пропускаем пустые записи
                if any(v for k, v in rec.items() if k != "source" and v):
                    results.append(rec)

            log.debug("scylla_search: найдено %d записей", len(results))
            return {"found": len(results), "results": results}

    except Exception as e:
        log.error("scylla_search: %s", e)
        return {"error": str(e)}
