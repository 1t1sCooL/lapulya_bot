"""
LeakCheck.io API — поиск утечек по email, phone, username, name, keyword, domain.
Docs: https://leakcheck.io/api
Тариф: платный, есть пробный период.
"""
import httpx
from config import REQUEST_TIMEOUT

LEAKCHECK_API = "https://leakcheck.io/api/v2"


async def leakcheck_search(query: str, api_key: str, query_type: str = "auto") -> dict:
    """
    query_type: auto | email | phone | username | name | keyword | domain
    Возвращает список записей из утечек.
    """
    if not api_key:
        return {"error": "LEAKCHECK_API_KEY не задан"}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"{LEAKCHECK_API}/query/{query}",
                headers={"X-API-Key": api_key},
                params={"type": query_type},
            )
            if r.status_code == 401:
                return {"error": "Неверный API ключ LeakCheck"}
            if r.status_code == 402:
                return {"error": "Недостаточно кредитов LeakCheck"}
            if r.status_code == 429:
                return {"error": "Rate limit LeakCheck"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            data = r.json()
            if not data.get("success"):
                return {"error": data.get("error", "Неизвестная ошибка")}

            results = data.get("result", [])
            return {
                "found": len(results),
                "query": query,
                "results": [_normalize_leakcheck(rec) for rec in results[:50]],
                "sources": data.get("sources", []),
            }
    except Exception as e:
        return {"error": str(e)}


def _normalize_leakcheck(rec: dict) -> dict:
    return {
        "email": rec.get("email", ""),
        "username": rec.get("username", ""),
        "password": rec.get("password", ""),
        "password_hash": rec.get("hash", ""),
        "phone": rec.get("phone", ""),
        "name": rec.get("name", ""),
        "source": rec.get("sources", [{}])[0].get("name", "?") if rec.get("sources") else "?",
        "last_breach": rec.get("sources", [{}])[0].get("date", "?") if rec.get("sources") else "?",
    }


async def leakcheck_public(email: str) -> dict:
    """
    Публичный эндпоинт LeakCheck — список источников утечек без паролей.
    Не требует API-ключа. Только для email-адресов.
    """
    import logging
    log = logging.getLogger(__name__)
    log.debug("leakcheck_public: %r", email)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"https://leakcheck.io/api/public",
                params={"check": email},
            )
            log.debug("leakcheck_public: HTTP %d", r.status_code)
            if r.status_code == 429:
                return {"error": "LeakCheck public: rate limit"}
            if r.status_code != 200:
                return {"error": f"LeakCheck public: HTTP {r.status_code}"}
            data = r.json()
            if not data.get("success"):
                return {"error": data.get("error", "unknown")}
            sources = data.get("sources", [])
            log.debug("leakcheck_public: найдено %d источников, записей=%d", len(sources), data.get("found", 0))
            return {
                "found": data.get("found", 0),
                "sources": sources[:50],
            }
    except Exception as e:
        log.error("leakcheck_public: %s", e)
        return {"error": str(e)}
