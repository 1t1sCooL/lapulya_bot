import logging
import re
import urllib.parse
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OSINTBot/1.0)",
    "Accept": "application/json",
}

# Паттерн кадастрового номера: XX:XX:XXXXXXX:XX
CADASTRAL_RE = re.compile(r'^\d{2}:\d{2}:\d{6,7}:\d+$')


def is_cadastral(query: str) -> bool:
    return bool(CADASTRAL_RE.match(query.strip()))


async def address_search(query: str) -> dict:
    """Поиск адреса через ФИАС и 2GIS."""
    log.debug("address_search: запрос %r", query)

    import asyncio
    fias_task = asyncio.create_task(_fias_search(query))
    gis_task = asyncio.create_task(_2gis_search(query))

    fias_results, gis_results = await asyncio.gather(fias_task, gis_task, return_exceptions=True)

    if isinstance(fias_results, Exception):
        log.error("address_search: ФИАС упал: %s", fias_results)
        fias_results = []
    if isinstance(gis_results, Exception):
        log.error("address_search: 2GIS упал: %s", gis_results)
        gis_results = []

    all_results: list[dict] = []
    if isinstance(fias_results, list):
        all_results.extend(fias_results)
    if isinstance(gis_results, list):
        all_results.extend(gis_results)

    if not all_results:
        return {"error": "Адрес не найден", "results": [], "found": 0}

    return {"results": all_results, "found": len(all_results)}


async def _fias_search(query: str) -> list[dict]:
    """Поиск через публичный API ФИАС nalog.ru."""
    results: list[dict] = []

    # Попытка 1: suggest API
    url1 = "https://fias-public-service.nalog.ru/api/private/suggest/address"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS) as client:
            r = await client.post(url1, json={"query": query, "count": 5})
            log.debug("ФИАС suggest: %s → %d", url1, r.status_code)
            if r.status_code == 200:
                data = r.json()
                items = data if isinstance(data, list) else data.get("suggestions", []) or data.get("addresses", []) or []
                for item in items[:5]:
                    addr = _parse_fias_item(item)
                    if addr:
                        results.append(addr)
    except Exception as exc:
        log.debug("ФИАС suggest: ошибка %s", exc)

    if results:
        return results

    # Попытка 2: Search endpoint
    url2 = f"https://fias.nalog.ru/Search?text={urllib.parse.quote(query)}&limit=5"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers={
            **HEADERS, "Accept": "text/html,application/json"
        }) as client:
            r = await client.get(url2)
            log.debug("ФИАС search: %s → %d", url2, r.status_code)
            if r.status_code == 200:
                try:
                    data = r.json()
                    items = data if isinstance(data, list) else data.get("results", []) or []
                    for item in items[:5]:
                        addr = _parse_fias_item(item)
                        if addr:
                            results.append(addr)
                except Exception:
                    pass
    except Exception as exc:
        log.debug("ФИАС search: ошибка %s", exc)

    return results


def _parse_fias_item(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None

    address = (
        item.get("full_name")
        or item.get("fullName")
        or item.get("address")
        or item.get("value")
        or item.get("unrestricted_value")
        or ""
    )
    if not address:
        # попробовать склеить поля
        parts = [
            item.get("region_with_type"),
            item.get("city_with_type") or item.get("settlement_with_type"),
            item.get("street_with_type"),
            item.get("house"),
        ]
        address = ", ".join(p for p in parts if p)

    if not address:
        return None

    data_block = item.get("data") or {}
    return {
        "address": address.strip(),
        "region": item.get("region") or data_block.get("region_with_type", ""),
        "city": item.get("city") or data_block.get("city", ""),
        "street": item.get("street") or data_block.get("street_with_type", ""),
        "house": item.get("house") or data_block.get("house", ""),
        "lat": item.get("lat") or data_block.get("geo_lat"),
        "lon": item.get("lon") or data_block.get("geo_lon"),
        "source": "ФИАС",
        "fias_id": item.get("guid") or data_block.get("fias_id", ""),
    }


async def _2gis_search(query: str) -> list[dict]:
    """Поиск через публичный API 2GIS."""
    url = "https://catalog.api.2gis.com/3.0/suggests"
    params = {
        "q": query,
        "locale": "ru_RU",
        "type": "street,building",
        "fields": "items.full_name,items.point",
        "key": "ruMm4y",
        "limit": 5,
    }
    results: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS) as client:
            r = await client.get(url, params=params)
            log.debug("2GIS: %s → %d", url, r.status_code)
            if r.status_code != 200:
                return results
            data = r.json()
            items = data.get("result", {}).get("items", [])
            for item in items[:5]:
                addr: dict = {
                    "address": item.get("full_name") or item.get("name") or "",
                    "source": "2GIS",
                }
                point = item.get("point")
                if point:
                    addr["lat"] = point.get("lat")
                    addr["lon"] = point.get("lon")
                if addr["address"]:
                    results.append(addr)
    except Exception as exc:
        log.error("2GIS search: ошибка %s", exc)
    return results


async def rosreestr_lookup(cadastral: str) -> dict:
    """Получает информацию об объекте недвижимости по кадастровому номеру (Росреестр ПКК)."""
    cadastral = cadastral.strip()
    log.debug("rosreestr_lookup: %r", cadastral)

    url = f"https://pkk.rosreestr.ru/api/features/5/{urllib.parse.quote(cadastral)}"
    headers = {
        **HEADERS,
        "Referer": "https://pkk.rosreestr.ru/",
        "Origin": "https://pkk.rosreestr.ru",
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=headers, follow_redirects=True) as client:
            r = await client.get(url)
            log.debug("Росреестр: %s → %d", url, r.status_code)
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}
            data = r.json()

            feature = data.get("feature")
            if not feature:
                return {"error": "Объект не найден в ПКК"}

            attrs = feature.get("attrs", {})
            return {
                "cadastral": cadastral,
                "address": attrs.get("address"),
                "area": attrs.get("area_value"),
                "area_unit": attrs.get("area_unit"),
                "type": attrs.get("type_name") or attrs.get("category_type"),
                "status": attrs.get("status"),
                "cost": attrs.get("cad_cost"),
                "date": attrs.get("date_cost") or attrs.get("date_create"),
                "rights_reg": attrs.get("rights_reg"),
                "source": "Росреестр ПКК",
            }
    except httpx.RequestError as exc:
        log.error("rosreestr_lookup: ошибка сети %s", exc)
        return {"error": f"Ошибка сети: {exc}"}
    except Exception as exc:
        log.error("rosreestr_lookup: неожиданная ошибка %s", exc)
        return {"error": str(exc)}
