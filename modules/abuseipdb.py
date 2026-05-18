"""
AbuseIPDB — база жалоб на IP-адреса (спам, атаки, сканирование).
Бесплатный tier: 1000 req/день. Нужен бесплатный API ключ.
Docs: https://docs.abuseipdb.com
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

ABUSEIPDB_API = "https://api.abuseipdb.com/api/v2"


async def abuseipdb_check(ip: str, api_key: str, max_age_days: int = 90) -> dict:
    """
    Проверяет IP по базе жалоб AbuseIPDB.
    Возвращает: счёт злоупотреблений, число жалоб, страну, ISP, категории атак.
    """
    if not api_key:
        return {"error": "ABUSEIPDB_API_KEY не задан"}
    log.debug("abuseipdb_check: %r", ip)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"{ABUSEIPDB_API}/check",
                headers={"Key": api_key, "Accept": "application/json"},
                params={
                    "ipAddress": ip,
                    "maxAgeInDays": max_age_days,
                    "verbose": True,
                },
            )
            log.debug("abuseipdb_check: HTTP %d", r.status_code)
            if r.status_code == 422:
                return {"error": "AbuseIPDB: некорректный IP"}
            if r.status_code == 429:
                return {"error": "AbuseIPDB: rate limit"}
            if r.status_code == 401:
                return {"error": "AbuseIPDB: неверный API ключ"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            d = r.json().get("data", {})
            reports = d.get("reports", [])

            # Расшифровка категорий атак
            cat_names = {
                1: "DNS Компромисс", 2: "DNS Отравление", 3: "Мошенничество/Фишинг",
                4: "DDoS атака", 5: "FTP брутфорс", 6: "Ping-сканирование",
                7: "Фишинг", 8: "Мошенничество/VoIP", 9: "Открытый прокси",
                10: "Веб-спам", 11: "Email-спам", 12: "Блог-спам",
                13: "VPN IP", 14: "Port scan", 15: "Взлом",
                16: "SQL инъекция", 17: "Спуфинг email", 18: "Brute-Force",
                19: "Bad Web Bot", 20: "Exploit CMS", 21: "Веб-атака",
                22: "SSH брутфорс", 23: "IoT-атака",
            }
            all_cats = set()
            for rep in reports[:20]:
                for c in rep.get("categories", []):
                    all_cats.add(cat_names.get(c, f"Cat{c}"))

            return {
                "ip":             d.get("ipAddress", ip),
                "abuse_score":    d.get("abuseConfidenceScore", 0),   # 0-100
                "total_reports":  d.get("totalReports", 0),
                "country":        d.get("countryCode", ""),
                "isp":            d.get("isp", ""),
                "domain":         d.get("domain", ""),
                "usage_type":     d.get("usageType", ""),
                "last_reported":  d.get("lastReportedAt", ""),
                "is_tor":         d.get("isTor", False),
                "is_public":      d.get("isPublic", True),
                "categories":     sorted(all_cats),
                "hostnames":      d.get("hostnames", [])[:5],
            }
    except Exception as e:
        log.error("abuseipdb_check: %s", e)
        return {"error": str(e)}
