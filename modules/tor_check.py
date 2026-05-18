"""
Проверка IP на принадлежность к Tor-сети.
Бесплатно, без ключа. Два источника для надёжности.
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)


async def is_tor_exit(ip: str) -> dict:
    """
    Проверяет, является ли IP Tor exit node.
    Возвращает: {"is_tor": bool, "source": str}
    """
    log.debug("is_tor_exit: %r", ip)
    # Источник 1: Tor Project официальный API
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://check.torproject.org/api/ip",
                params={"ip": ip},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                d = r.json()
                return {"is_tor": bool(d.get("IsTor")), "source": "TorProject"}
    except Exception as e:
        log.debug("tor_check torproject: %s", e)

    # Источник 2: Dan.me.uk bulk exit list
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://www.dan.me.uk/torcheck?ip={ip}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                is_tor = "is a tor" in r.text.lower() or "exit node" in r.text.lower()
                return {"is_tor": is_tor, "source": "dan.me.uk"}
    except Exception as e:
        log.debug("tor_check dan.me.uk: %s", e)

    return {"is_tor": False, "source": "unknown"}
