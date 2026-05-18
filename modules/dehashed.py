"""
Dehashed API — поиск в 15+ млрд записях из утечек по email, username, IP, address, phone, name, VIN.
Docs: https://www.dehashed.com/docs
Требует: email (аккаунт) + API key. Платный.
"""
import httpx
import base64
from config import REQUEST_TIMEOUT

DEHASHED_API = "https://api.dehashed.com/search"


async def dehashed_search(
    query: str,
    email: str,
    api_key: str,
    field: str = "email",
    page: int = 1,
    size: int = 20,
) -> dict:
    """
    field: email | username | ip_address | name | address | phone | vin | domain
    Результаты содержат: email, username, password, hashed_password, name, address, phone, database_name
    """
    if not api_key or not email:
        return {"error": "DEHASHED_EMAIL и DEHASHED_API_KEY должны быть заданы"}

    # Dehashed использует Basic Auth: email:api_key
    creds = base64.b64encode(f"{email}:{api_key}".encode()).decode()

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                DEHASHED_API,
                headers={
                    "Authorization": f"Basic {creds}",
                    "Accept": "application/json",
                },
                params={
                    "query": f"{field}:{query}",
                    "page": page,
                    "size": size,
                },
            )
            if r.status_code == 401:
                return {"error": "Неверные Dehashed credentials"}
            if r.status_code == 400:
                return {"error": "Неверный запрос к Dehashed"}
            if r.status_code == 429:
                return {"error": "Rate limit Dehashed"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            data = r.json()
            entries = data.get("entries") or []
            return {
                "total": data.get("total", 0),
                "found": len(entries),
                "balance": data.get("balance"),
                "results": [_normalize_dehashed(e) for e in entries],
            }
    except Exception as e:
        return {"error": str(e)}


def _normalize_dehashed(entry: dict) -> dict:
    return {
        "email": entry.get("email", ""),
        "username": entry.get("username", ""),
        "password": entry.get("password", ""),
        "hashed_password": entry.get("hashed_password", ""),
        "name": entry.get("name", ""),
        "address": entry.get("address", ""),
        "phone": entry.get("phone", ""),
        "database": entry.get("database_name", "?"),
        "ip": entry.get("ip_address", ""),
    }
