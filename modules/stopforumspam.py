"""
StopForumSpam.com — база известных спамеров и мошенников.
Бесплатно, без ключа. Проверяет email, IP, username.
Docs: https://www.stopforumspam.com/usage
"""
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

SFS_API = "https://api.stopforumspam.org/api"


async def sfs_check(query: str, query_type: str = "email") -> dict:
    """
    query_type: email | ip | username
    Возвращает: найден ли в базе спамеров, частота появления, последнее появление.
    """
    log.debug("sfs_check: %r type=%s", query, query_type)
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(
                SFS_API,
                params={query_type: query, "json": 1},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            log.debug("sfs_check: HTTP %d", r.status_code)
            if r.status_code != 200:
                return {"error": f"SFS: HTTP {r.status_code}"}

            d = r.json()
            result = d.get(query_type, {})
            found = bool(result.get("appears", 0))
            return {
                "found":       found,
                "frequency":   result.get("frequency", 0),
                "lastseen":    result.get("lastseen", ""),
                "confidence":  result.get("confidence", 0),
                "delegated":   result.get("delegated", ""),
            }
    except Exception as e:
        log.error("sfs_check: %s", e)
        return {"error": str(e)}


async def sfs_check_multi(email: str = "", ip: str = "", username: str = "") -> dict:
    """Проверяет несколько типов за один запрос."""
    log.debug("sfs_check_multi email=%r ip=%r user=%r", email, ip, username)
    params: dict = {"json": 1}
    if email:    params["email"]    = email
    if ip:       params["ip"]       = ip
    if username: params["username"] = username
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(SFS_API, params=params)
            if r.status_code != 200:
                return {"error": f"SFS: HTTP {r.status_code}"}
            d = r.json()
            out = {}
            for key in ("email", "ip", "username"):
                if key in d:
                    rec = d[key]
                    out[key] = {
                        "found":      bool(rec.get("appears", 0)),
                        "frequency":  rec.get("frequency", 0),
                        "lastseen":   rec.get("lastseen", ""),
                        "confidence": rec.get("confidence", 0),
                    }
            return out
    except Exception as e:
        log.error("sfs_check_multi: %s", e)
        return {"error": str(e)}
