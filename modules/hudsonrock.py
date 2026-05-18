"""
Hudson Rock Cavalier — бесплатный поиск данных об инфостилерах.
Показывает заражённые компьютеры, где были сохранены учётные данные жертвы.
Docs: https://www.hudsonrock.com/free-tools
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

CAVALIER_API = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools"


async def hudsonrock_email(email: str) -> dict:
    """Поиск по email — заражённые компьютеры с сохранёнными учётными данными."""
    return await _cavalier_search("search-by-email", {"email": email})


async def hudsonrock_username(username: str) -> dict:
    """Поиск по username."""
    return await _cavalier_search("search-by-username", {"username": username})


async def hudsonrock_domain(domain: str) -> dict:
    """Поиск по домену — все заражённые сотрудники/пользователи."""
    return await _cavalier_search("search-by-domain", {"domain": domain})


async def _cavalier_search(endpoint: str, params: dict) -> dict:
    log.debug("hudsonrock %s: %s", endpoint, params)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(f"{CAVALIER_API}/{endpoint}", params=params)
            log.debug("hudsonrock: HTTP %d", r.status_code)
            if r.status_code == 404:
                return {"stealers": [], "total": 0}
            if r.status_code != 200:
                return {"error": f"HudsonRock HTTP {r.status_code}"}
            data = r.json()
            stealers = data.get("stealers", [])
            log.debug("hudsonrock: найдено %d заражений", len(stealers))
            result = []
            for s in stealers[:10]:
                result.append({
                    "date": s.get("date_compromised", "")[:10],
                    "computer": s.get("computer_name", ""),
                    "os": s.get("operating_system", ""),
                    "malware": s.get("malware_path", ""),
                    "ip": s.get("ip", ""),
                    "total_services": s.get("total_user_services", 0),
                    "top_logins": s.get("top_logins", [])[:3],
                })
            return {
                "found": len(stealers),
                "stealers": result,
                "total_corporate": data.get("total_corporate_services", 0),
                "total_user": data.get("total_user_services", 0),
            }
    except Exception as e:
        log.error("hudsonrock: %s", e)
        return {"error": str(e)}
