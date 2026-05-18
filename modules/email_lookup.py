import re
import httpx
from config import HIBP_API_KEY, REQUEST_TIMEOUT

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


async def hibp_check(email: str) -> dict:
    """Проверяет email через HaveIBeenPwned API v3."""
    if not HIBP_API_KEY:
        return {"error": "HIBP_API_KEY не задан"}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                headers={
                    "hibp-api-key": HIBP_API_KEY,
                    "user-agent": "OSINTBot/1.0",
                },
                params={"truncateResponse": "false"},
            )
            if r.status_code == 200:
                breaches = r.json()
                return {
                    "breached": True,
                    "count": len(breaches),
                    "breaches": [
                        {
                            "name": b["Name"],
                            "date": b.get("BreachDate", "?"),
                            "data_classes": b.get("DataClasses", []),
                            "pwn_count": b.get("PwnCount", 0),
                        }
                        for b in breaches
                    ],
                }
            if r.status_code == 404:
                return {"breached": False}
            return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


async def email_domain_mx(email: str) -> list[str]:
    """Проверяет MX-записи домена почты."""
    import dns.resolver
    import asyncio
    domain = email.split("@")[-1]
    loop = asyncio.get_event_loop()
    try:
        answers = await loop.run_in_executor(
            None, lambda: dns.resolver.resolve(domain, "MX")
        )
        return sorted([str(r.exchange) for r in answers])
    except Exception:
        return []
