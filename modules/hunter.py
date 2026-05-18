"""
Hunter.io — поиск email-адресов по домену и имени.
Free tier: 100 запросов/месяц.
Docs: https://hunter.io/api-documentation/v2
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

HUNTER_API = "https://api.hunter.io/v2"


async def hunter_domain_search(domain: str, api_key: str, limit: int = 20) -> dict:
    """
    Возвращает все известные email-адреса на домене.
    Полезно для OSINT по организации.
    """
    if not api_key:
        return {"error": "HUNTER_API_KEY не задан"}
    log.debug("hunter_domain_search: %r", domain)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"{HUNTER_API}/domain-search",
                params={"domain": domain, "limit": limit, "api_key": api_key},
            )
            log.debug("hunter_domain_search: HTTP %d", r.status_code)
            if r.status_code == 401:
                return {"error": "Hunter: неверный API ключ"}
            if r.status_code == 429:
                return {"error": "Hunter: rate limit"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            d = r.json().get("data", {})
            emails = d.get("emails", [])
            return {
                "domain":       d.get("domain", domain),
                "organization": d.get("organization", ""),
                "total":        d.get("total", 0),
                "found":        len(emails),
                "emails": [
                    {
                        "email":      e.get("value", ""),
                        "first_name": e.get("first_name", ""),
                        "last_name":  e.get("last_name", ""),
                        "position":   e.get("position", ""),
                        "confidence": e.get("confidence", 0),
                        "sources":    len(e.get("sources", [])),
                    }
                    for e in emails[:30]
                ],
            }
    except Exception as e:
        log.error("hunter_domain_search: %s", e)
        return {"error": str(e)}


async def hunter_email_finder(first_name: str, last_name: str, domain: str, api_key: str) -> dict:
    """
    Находит email конкретного человека по имени и домену.
    Например: Иван Петров + example.com → ivan.petrov@example.com
    """
    if not api_key:
        return {"error": "HUNTER_API_KEY не задан"}
    log.debug("hunter_email_finder: %r %r @ %r", first_name, last_name, domain)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"{HUNTER_API}/email-finder",
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": api_key,
                },
            )
            if r.status_code == 429:
                return {"error": "Hunter: rate limit"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            d = r.json().get("data", {})
            return {
                "email":      d.get("email", ""),
                "confidence": d.get("score", 0),
                "sources":    len(d.get("sources", [])),
                "first_name": d.get("first_name", ""),
                "last_name":  d.get("last_name", ""),
            }
    except Exception as e:
        log.error("hunter_email_finder: %s", e)
        return {"error": str(e)}


async def hunter_verify(email: str, api_key: str) -> dict:
    """
    Проверяет существование email-адреса (валидация).
    """
    if not api_key:
        return {"error": "HUNTER_API_KEY не задан"}
    log.debug("hunter_verify: %r", email)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"{HUNTER_API}/email-verifier",
                params={"email": email, "api_key": api_key},
            )
            if r.status_code == 429:
                return {"error": "Hunter: rate limit"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            d = r.json().get("data", {})
            return {
                "email":       d.get("email", email),
                "status":      d.get("status", ""),         # valid / invalid / accept_all / webmail / disposable / unknown
                "result":      d.get("result", ""),         # deliverable / risky / undeliverable
                "score":       d.get("score", 0),
                "regexp":      d.get("regexp", False),
                "gibberish":   d.get("gibberish", False),
                "disposable":  d.get("disposable", False),
                "webmail":     d.get("webmail", False),
                "mx_records":  d.get("mx_records", False),
                "smtp_server": d.get("smtp_server", False),
                "smtp_check":  d.get("smtp_check", False),
            }
    except Exception as e:
        log.error("hunter_verify: %s", e)
        return {"error": str(e)}
