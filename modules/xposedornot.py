"""
XposedOrNot — бесплатный поиск email по 400+ базам утечек.
Docs: https://xposedornot.com/api_doc
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

XON_API = "https://api.xposedornot.com/v1"


async def xon_check_email(email: str) -> dict:
    """
    Возвращает список утечек где засветился email + риск-скор + категории данных.
    Два запроса параллельно: check-email (список) + breach-analytics (детали).
    """
    import asyncio
    log.debug("xon_check_email: %r", email)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r1, r2 = await asyncio.gather(
                client.get(f"{XON_API}/check-email/{email}"),
                client.get(f"{XON_API}/breach-analytics", params={"email": email}),
            )
            log.debug("xon check=%d analytics=%d", r1.status_code, r2.status_code)

            breaches = []
            if r1.status_code == 200:
                d1 = r1.json()
                raw = d1.get("breaches", [[]])[0] if d1.get("breaches") else []
                breaches = raw if isinstance(raw, list) else []

            risk_label, risk_score = "", 0
            passwords = {}
            exposed_categories = []
            yearwise = {}

            if r2.status_code == 200:
                bm = r2.json().get("BreachMetrics", {})
                risk_list = bm.get("risk") or []
                if risk_list:
                    risk_label = risk_list[0].get("risk_label", "")
                    risk_score = risk_list[0].get("risk_score", 0)
                passwords = (bm.get("passwords_strength") or [{}])[0]
                # Собираем категории данных
                for cat in bm.get("xposed_data", []):
                    for child in cat.get("children", []):
                        val = child.get("value", 0)
                        if val > 0:
                            name = child.get("name", "").replace("data_", "")
                            exposed_categories.append({"name": name, "count": val})
                # По годам
                for yw in bm.get("yearwise_details", []):
                    for item in yw if isinstance(yw, list) else []:
                        if isinstance(item, list) and len(item) == 2:
                            yearwise[str(item[0])] = item[1]

            log.debug("xon: найдено %d утечек, риск=%s(%d)", len(breaches), risk_label, risk_score)
            return {
                "found": len(breaches),
                "breaches": breaches,
                "risk_label": risk_label,
                "risk_score": risk_score,
                "passwords": passwords,
                "exposed_categories": sorted(exposed_categories, key=lambda x: -x["count"])[:10],
                "yearwise": yearwise,
            }
    except Exception as e:
        log.error("xon_check_email: %s", e)
        return {"error": str(e)}


async def pwned_password(password: str) -> int:
    """
    HIBP Pwned Passwords — проверяет пароль через k-anonymity (SHA1).
    Возвращает количество раз пароль встречался в утечках (0 = не найден).
    Пароль НЕ передаётся на сервер — только первые 5 символов хэша.
    """
    import hashlib
    log.debug("pwned_password: проверка пароля")
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"Add-Padding": "true"},
            )
            if r.status_code != 200:
                return -1
            for line in r.text.splitlines():
                parts = line.split(":")
                if len(parts) == 2 and parts[0] == suffix:
                    count = int(parts[1].strip())
                    log.debug("pwned_password: найден %d раз", count)
                    return count
            return 0
    except Exception as e:
        log.error("pwned_password: %s", e)
        return -1
