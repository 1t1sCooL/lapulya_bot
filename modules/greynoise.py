"""
GreyNoise Community API — threat intelligence по IP-адресам.
Бесплатный community tier: 100 req/день, нужен бесплатный API ключ.
Docs: https://docs.greynoise.io/reference
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

GREYNOISE_API = "https://api.greynoise.io/v3"


async def greynoise_ip(ip: str, api_key: str) -> dict:
    """
    Проверяет IP: сканирует ли он интернет, вредоносный ли, откуда.
    Возвращает classification, name, tags, first/last_seen и т.д.
    """
    if not api_key:
        return {"error": "GREYNOISE_API_KEY не задан"}
    log.debug("greynoise_ip: %r", ip)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"{GREYNOISE_API}/community/{ip}",
                headers={"key": api_key},
            )
            log.debug("greynoise_ip: HTTP %d", r.status_code)
            if r.status_code == 404:
                return {"found": False, "message": "IP не найден в GreyNoise"}
            if r.status_code == 429:
                return {"error": "GreyNoise: rate limit"}
            if r.status_code == 401:
                return {"error": "GreyNoise: неверный API ключ"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            d = r.json()
            return {
                "found":          True,
                "ip":             d.get("ip", ip),
                "noise":          d.get("noise", False),       # активно сканирует
                "riot":           d.get("riot", False),        # известный безопасный сервис
                "classification": d.get("classification", ""), # malicious/benign/unknown
                "name":           d.get("name", ""),
                "link":           d.get("link", ""),
                "last_seen":      d.get("last_seen", ""),
                "message":        d.get("message", ""),
            }
    except Exception as e:
        log.error("greynoise_ip: %s", e)
        return {"error": str(e)}
