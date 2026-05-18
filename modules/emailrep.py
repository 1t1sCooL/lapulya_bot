"""
EmailRep.io — репутация email-адреса.
Бесплатно без ключа (лимит 100 req/день). С ключом — больше.
Docs: https://emailrep.io/docs
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)


async def emailrep_check(email: str, api_key: str = "") -> dict:
    """
    Возвращает репутацию email: риск, признаки подозрительности,
    наличие в утечках, соцсети, тип почты и т.д.
    """
    log.debug("emailrep_check: %r", email)
    headers = {"User-Agent": "osint-bot/1.0"}
    if api_key:
        headers["Key"] = api_key
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"https://emailrep.io/{email}",
                headers=headers,
            )
            log.debug("emailrep_check: HTTP %d", r.status_code)
            if r.status_code == 400:
                return {"error": "Некорректный email"}
            if r.status_code == 429:
                return {"error": "EmailRep: rate limit"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            d = r.json()
            details = d.get("details", {})
            return {
                "email":            d.get("email", email),
                "reputation":       d.get("reputation", "unknown"),  # none/low/medium/high
                "suspicious":       d.get("suspicious", False),
                "references":       d.get("references", 0),
                "blacklisted":      details.get("blacklisted", False),
                "malicious_activity": details.get("malicious_activity", False),
                "credentials_leaked": details.get("credentials_leaked", False),
                "credentials_leaked_recent": details.get("credentials_leaked_recent", False),
                "data_breach":      details.get("data_breach", False),
                "last_seen":        details.get("last_seen", ""),
                "spam":             details.get("spam", False),
                "free_provider":    details.get("free_provider", False),
                "disposable":       details.get("disposable", False),
                "deliverable":      details.get("deliverable", False),
                "profiles":         details.get("profiles", []),
                "domain_exists":    details.get("domain_exists", True),
                "domain_reputation": details.get("domain_reputation", ""),
            }
    except Exception as e:
        log.error("emailrep_check: %s", e)
        return {"error": str(e)}
