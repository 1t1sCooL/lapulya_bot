"""
NumVerify — валидация и обогащение номеров телефонов.
Free tier: 250 запросов/месяц. Регистрация бесплатная.
Docs: https://numverify.com/documentation
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

NUMVERIFY_API = "http://apilayer.net/api/validate"   # http, не https (free tier)


async def numverify_lookup(phone: str, api_key: str) -> dict:
    """
    Возвращает: валидность, страна, оператор, тип линии (mobile/landline/special_services).
    phone должен быть в формате E.164 без '+', например '79001234567'.
    """
    if not api_key:
        return {"error": "NUMVERIFY_API_KEY не задан"}
    log.debug("numverify_lookup: %r", phone)
    # Убираем + и пробелы
    clean = phone.lstrip("+").replace(" ", "").replace("-", "")
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                NUMVERIFY_API,
                params={
                    "access_key": api_key,
                    "number": clean,
                    "format": 1,
                },
            )
            log.debug("numverify_lookup: HTTP %d", r.status_code)
            if r.status_code != 200:
                return {"error": f"NumVerify: HTTP {r.status_code}"}
            d = r.json()
            if not d.get("valid") and "error" in d:
                return {"error": d["error"].get("info", "NumVerify error")}
            return {
                "valid":            d.get("valid", False),
                "number":           d.get("number", clean),
                "local_format":     d.get("local_format", ""),
                "international":    d.get("international_format", ""),
                "country_prefix":   d.get("country_prefix", ""),
                "country_code":     d.get("country_code", ""),
                "country_name":     d.get("country_name", ""),
                "location":         d.get("location", ""),
                "carrier":          d.get("carrier", ""),
                "line_type":        d.get("line_type", ""),    # mobile/landline/special_services
            }
    except Exception as e:
        log.error("numverify_lookup: %s", e)
        return {"error": str(e)}
