import logging
import httpx
from config import VK_TOKEN, REQUEST_TIMEOUT

log = logging.getLogger(__name__)

VK_API = "https://api.vk.com/method"
VK_VERSION = "5.199"


async def _vk_call(method: str, params: dict) -> dict:
    params = {**params, "access_token": VK_TOKEN, "v": VK_VERSION}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        r = await client.get(f"{VK_API}/{method}", params=params)
        data = r.json()
        if "error" in data:
            return {"error": data["error"].get("error_msg", "VK API error")}
        return data.get("response", {})


async def vk_user_lookup(user_id: str) -> dict:
    """Получает публичный профиль VK пользователя."""
    if not VK_TOKEN:
        return {"error": "VK_TOKEN не задан"}
    fields = "bdate,city,country,followers_count,occupation,relation,screen_name,sex,status,last_seen,photo_max_orig,connections,site,universities,schools"
    data = await _vk_call("users.get", {"user_ids": user_id, "fields": fields})
    if "error" in data:
        return data
    if isinstance(data, list) and data:
        u = data[0]
        return {
            "id": u.get("id"),
            "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
            "screen_name": u.get("screen_name"),
            "bdate": u.get("bdate"),
            "city": u.get("city", {}).get("title") if isinstance(u.get("city"), dict) else None,
            "country": u.get("country", {}).get("title") if isinstance(u.get("country"), dict) else None,
            "followers": u.get("followers_count"),
            "status": u.get("status"),
            "relation": _relation(u.get("relation")),
            "photo": u.get("photo_max_orig"),
            "site": u.get("site"),
            "is_closed": u.get("is_closed"),
            "deactivated": u.get("deactivated"),
            "last_seen": _fmt_last_seen(u.get("last_seen")),
        }
    return {"error": "Пользователь не найден"}


async def vk_user_search(name: str, count: int = 20) -> dict:
    """Ищет пользователей VK по имени через users.search."""
    if not VK_TOKEN:
        return {"error": "VK_TOKEN не задан"}
    log.debug("vk_user_search: поиск %r count=%d", name, count)
    fields = "bdate,city,country,followers_count,screen_name,photo_100,is_closed"
    data = await _vk_call("users.search", {"q": name, "fields": fields, "count": count})
    if "error" in data:
        log.error("vk_user_search: ошибка API %s", data["error"])
        return data
    items = data.get("items", []) if isinstance(data, dict) else []
    total = data.get("count", 0) if isinstance(data, dict) else 0
    log.debug("vk_user_search: найдено %d профилей (всего: %d)", len(items), total)
    results = []
    for u in items:
        results.append({
            "id": u.get("id"),
            "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
            "screen_name": u.get("screen_name"),
            "url": f"https://vk.com/{u.get('screen_name') or 'id' + str(u.get('id', ''))}",
            "city": (u.get("city") or {}).get("title", ""),
            "country": (u.get("country") or {}).get("title", ""),
            "bdate": u.get("bdate", ""),
            "followers": u.get("followers_count"),
            "photo": u.get("photo_100", ""),
            "is_closed": u.get("is_closed", False),
        })
    return {"results": results, "found": total}


async def vk_group_lookup(group_id: str) -> dict:
    """Получает публичную информацию о группе VK."""
    if not VK_TOKEN:
        return {"error": "VK_TOKEN не задан"}
    fields = "description,members_count,site,status,verified,activity,city,country"
    data = await _vk_call("groups.getById", {"group_ids": group_id, "fields": fields})
    if "error" in data:
        return data
    groups = data if isinstance(data, list) else data.get("groups", [])
    if groups:
        g = groups[0]
        return {
            "id": g.get("id"),
            "name": g.get("name"),
            "screen_name": g.get("screen_name"),
            "type": g.get("type"),
            "members_count": g.get("members_count"),
            "description": (g.get("description") or "")[:300],
            "site": g.get("site"),
            "verified": g.get("verified"),
            "status": g.get("status"),
            "city": g.get("city", {}).get("title") if isinstance(g.get("city"), dict) else None,
        }
    return {"error": "Группа не найдена"}


def _relation(code: int | None) -> str:
    mapping = {
        0: "Не указано", 1: "Не женат/замужем", 2: "Есть друг/подруга",
        3: "Помолвлен(а)", 4: "Женат/Замужем", 5: "Всё сложно",
        6: "В активном поиске", 7: "Влюблён(а)", 8: "В гражданском браке",
    }
    return mapping.get(code, "?")


def _fmt_last_seen(ls: dict | None) -> str:
    if not ls:
        return ""
    import datetime
    ts = ls.get("time", 0)
    dt = datetime.datetime.fromtimestamp(ts)
    platform = {1: "Mobile", 2: "iPhone", 3: "iPad", 4: "Android", 5: "WindowsPhone", 6: "Windows10", 7: "Web"}
    plat = platform.get(ls.get("platform", 0), "?")
    return f"{dt.strftime('%Y-%m-%d %H:%M')} ({plat})"
