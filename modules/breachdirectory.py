"""
BreachDirectory — поиск email/username в утечках через RapidAPI.
Бесплатный tier: 10 запросов/мес. Платный: 100–∞.
Docs: https://rapidapi.com/rohan-patra/api/breachdirectory
"""
import httpx
from config import REQUEST_TIMEOUT

BREACHDIR_API = "https://breachdirectory.p.rapidapi.com/"


async def breachdirectory_search(query: str, rapidapi_key: str) -> dict:
    """Ищет по email или username. Возвращает хэши и источники без plain-text паролей."""
    if not rapidapi_key:
        return {"error": "RAPIDAPI_KEY не задан"}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                BREACHDIR_API,
                headers={
                    "X-RapidAPI-Key": rapidapi_key,
                    "X-RapidAPI-Host": "breachdirectory.p.rapidapi.com",
                },
                params={"func": "auto", "term": query},
            )
            if r.status_code == 403:
                return {"error": "Неверный RapidAPI ключ"}
            if r.status_code == 429:
                return {"error": "Rate limit RapidAPI"}
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}

            data = r.json()
            if not data.get("found"):
                return {"found": False, "results": []}

            results = data.get("result", [])
            return {
                "found": True,
                "count": len(results),
                "results": [
                    {
                        "hash": r.get("hash", ""),
                        "sha1": r.get("sha1", ""),
                        "sources": r.get("sources", []),
                        "password": r.get("password", ""),  # может быть пустым
                    }
                    for r in results[:30]
                ],
            }
    except Exception as e:
        return {"error": str(e)}
