"""
IPQualityScore — качество и репутация IP-адресов и email.
Free tier: 500 запросов/месяц.
Docs: https://www.ipqualityscore.com/documentation
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

IPQS_API = "https://ipqualityscore.com/api/json"


async def ipqs_ip(ip: str, api_key: str) -> dict:
    """
    Проверяет IP: фрод-скор, прокси/VPN/Tor, бот, страна, ISP.
    """
    if not api_key:
        return {"error": "IPQS_API_KEY не задан"}
    log.debug("ipqs_ip: %r", ip)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"{IPQS_API}/ip/{api_key}/{ip}",
                params={"strictness": 1, "allow_public_access_points": True},
            )
            log.debug("ipqs_ip: HTTP %d", r.status_code)
            if r.status_code == 429:
                return {"error": "IPQS: rate limit"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            d = r.json()
            if not d.get("success"):
                return {"error": d.get("message", "IPQS error")}
            return {
                "fraud_score":      d.get("fraud_score", 0),         # 0-100, >75 = подозрительный
                "proxy":            d.get("proxy", False),
                "vpn":              d.get("vpn", False),
                "tor":              d.get("tor", False),
                "bot_status":       d.get("bot_status", False),
                "is_crawler":       d.get("is_crawler", False),
                "recent_abuse":     d.get("recent_abuse", False),
                "country_code":     d.get("country_code", ""),
                "region":           d.get("region", ""),
                "city":             d.get("city", ""),
                "isp":              d.get("ISP", ""),
                "organization":     d.get("organization", ""),
                "asn":              d.get("ASN", 0),
                "connection_type":  d.get("connection_type", ""),     # Residential/Mobile/Corporate/Data Center
                "abuse_velocity":   d.get("abuse_velocity", ""),
                "timezone":         d.get("timezone", ""),
                "latitude":         d.get("latitude"),
                "longitude":        d.get("longitude"),
            }
    except Exception as e:
        log.error("ipqs_ip: %s", e)
        return {"error": str(e)}


async def ipqs_email(email: str, api_key: str) -> dict:
    """
    Проверяет email: фрод-скор, одноразовый, валидный, утечки и т.д.
    """
    if not api_key:
        return {"error": "IPQS_API_KEY не задан"}
    log.debug("ipqs_email: %r", email)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"{IPQS_API}/email/{api_key}/{email}",
                params={"strictness": 1, "timeout": 7},
            )
            log.debug("ipqs_email: HTTP %d", r.status_code)
            if r.status_code == 429:
                return {"error": "IPQS: rate limit"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            d = r.json()
            if not d.get("success"):
                return {"error": d.get("message", "IPQS error")}
            return {
                "fraud_score":    d.get("fraud_score", 0),
                "valid":          d.get("valid", False),
                "disposable":     d.get("disposable", False),
                "smtp_score":     d.get("smtp_score", 0),          # -1=нет MX, 0-3 = надёжность
                "overall_score":  d.get("overall_score", 0),
                "spam_trap":      d.get("spam_trap_score", ""),
                "leaked":         d.get("leaked", False),           # найден в утечках
                "suggested_domain": d.get("suggested_domain", ""),
                "domain_age_days": (d.get("domain_age") or {}).get("days", 0),
                "first_seen_days": (d.get("first_seen") or {}).get("days", 0),
                "deliverability": d.get("deliverability", ""),      # high/medium/low
                "frequent_complainer": d.get("frequent_complainer", False),
                "honeypot":       d.get("honeypot", False),
            }
    except Exception as e:
        log.error("ipqs_email: %s", e)
        return {"error": str(e)}
