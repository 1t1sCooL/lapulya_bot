"""
Wayback Machine (archive.org) — история сайта, снапшоты, удалённые страницы.
Бесплатно, без ключа.
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)


async def wayback_availability(url: str) -> dict:
    """Последний доступный снапшот для URL."""
    log.debug("wayback_availability: %r", url)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                "https://archive.org/wayback/available",
                params={"url": url},
            )
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}
            d = r.json()
            snap = d.get("archived_snapshots", {}).get("closest", {})
            if not snap:
                return {"found": False, "url": url}
            return {
                "found":     True,
                "url":       url,
                "snapshot":  snap.get("url", ""),
                "timestamp": snap.get("timestamp", ""),   # YYYYMMDDHHmmss
                "status":    snap.get("status", ""),
            }
    except Exception as e:
        log.error("wayback_availability: %s", e)
        return {"error": str(e)}


async def wayback_history(url: str, limit: int = 10) -> dict:
    """
    Список последних N снапшотов через CDX API.
    Возвращает даты, статусы и ссылки на снапшоты.
    """
    log.debug("wayback_history: %r limit=%d", url, limit)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                "https://web.archive.org/cdx/search/cdx",
                params={
                    "url": url,
                    "output": "json",
                    "limit": limit,
                    "fl": "timestamp,statuscode,mimetype",
                    "filter": "statuscode:200",
                    "collapse": "timestamp:8",   # один снапшот в день
                    "from": "20150101",
                },
            )
            if r.status_code != 200:
                return {"error": f"CDX HTTP {r.status_code}"}
            rows = r.json()
            if not rows or len(rows) < 2:
                return {"found": False, "snapshots": []}
            # Первая строка — заголовки
            snapshots = []
            for row in rows[1:]:
                ts = row[0]   # YYYYMMDDHHmmss
                date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
                snapshots.append({
                    "date":    date,
                    "archive": f"https://web.archive.org/web/{ts}/{url}",
                    "status":  row[1],
                })
            return {"found": True, "snapshots": snapshots, "total": len(snapshots)}
    except Exception as e:
        log.error("wayback_history: %s", e)
        return {"error": str(e)}
