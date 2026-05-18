"""
OSINT-агрегатор — автоматически определяет тип запроса
и запускает все подходящие модули параллельно.
"""
import asyncio
import logging
import re

log = logging.getLogger(__name__)

# ── регулярные выражения для определения типа запроса ──────────────────────

_PHONE_RE = re.compile(
    r'^(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$'
)
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+$')
_INN_RE = re.compile(r'^\d{10}$|^\d{12}$')
_IP_RE = re.compile(r'^\d{1,3}(?:\.\d{1,3}){3}$')
_DOMAIN_RE = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
)
_URL_RE = re.compile(r'^https?://')
_CADASTRAL_RE = re.compile(r'^\d{2}:\d{2}:\d{6,7}:\d+$')
_CAR_RE = re.compile(
    r'^[А-ЯЁA-Z]\d{3}[А-ЯЁA-Z]{2}\d{2,3}$', re.IGNORECASE
)
_PASSPORT_RE = re.compile(r'^\d{4}\s?\d{6}$')
_FIO_RE = re.compile(r'^[А-ЯЁа-яё]{2,}\s+[А-ЯЁа-яё]{2,}(?:\s+[А-ЯЁа-яё]{2,})?$')


def detect_query_type(query: str) -> str:
    """
    Определяет тип OSINT-запроса.

    Returns одну из строк:
      "phone", "email", "inn_ul", "inn_fl", "domain", "ip",
      "username", "fio", "car", "passport", "cadastral"
    """
    q = query.strip()

    if _PHONE_RE.match(re.sub(r'[\s\-()]', '', q)):
        return "phone"
    if _EMAIL_RE.match(q):
        return "email"
    if _CADASTRAL_RE.match(q):
        return "cadastral"
    if _PASSPORT_RE.match(q):
        return "passport"
    if _INN_RE.match(q):
        return "inn_ul" if len(q) == 10 else "inn_fl"
    if _IP_RE.match(q):
        return "ip"
    if _URL_RE.match(q) or _DOMAIN_RE.match(q):
        return "domain"
    if _CAR_RE.match(q):
        return "car"
    if _FIO_RE.match(q):
        return "fio"
    # иначе — username / слово
    return "username"


async def osint_search(query: str, **cfg) -> dict:
    """
    Запускает все подходящие OSINT-модули и возвращает агрегированный результат.

    cfg может содержать ключи API:
      leakcheck_key, dehashed_email, dehashed_key, intelx_key, vk_token
    """
    q = query.strip()
    qtype = detect_query_type(q)
    log.debug("osint_search: query=%r type=%s", q, qtype)

    results: dict = {}

    if qtype == "phone":
        results = await _search_phone(q, cfg)
    elif qtype == "email":
        results = await _search_email(q, cfg)
    elif qtype in ("inn_ul", "inn_fl"):
        results = await _search_inn(q, qtype)
    elif qtype == "domain":
        results = await _search_domain(q)
    elif qtype == "ip":
        results = await _search_ip(q)
    elif qtype == "username":
        results = await _search_username(q, cfg)
    elif qtype == "fio":
        results = await _search_fio(q, cfg)
    elif qtype == "car":
        results = await _search_car(q)
    elif qtype == "passport":
        results = await _search_passport(q)
    elif qtype == "cadastral":
        results = await _search_cadastral(q)

    return {"query_type": qtype, "query": q, "results": results}


# ── helpers ────────────────────────────────────────────────────────────────

async def _safe(coro, name: str):
    """Выполняет корутину, возвращает результат или {"error": ...}."""
    try:
        return await coro
    except Exception as exc:
        log.error("osint_search [%s]: %s", name, exc)
        return {"error": str(exc)}


async def _search_phone(q: str, cfg: dict) -> dict:
    from modules.phone_lookup import parse_phone
    from modules.leakcheck import leakcheck_search
    from modules.getcontact import getcontact_search
    from modules.vk_lookup import vk_user_search

    phone_info = parse_phone(q)
    e164 = phone_info.get("e164", q)

    async def _phone_info_wrap():
        return phone_info

    tasks = {
        "phone_info": asyncio.create_task(_safe(_phone_info_wrap(), "phone_info")),
        "leakcheck": asyncio.create_task(_safe(
            leakcheck_search(e164, api_key=cfg.get("leakcheck_key", "")), "leakcheck"
        )),
        "getcontact": asyncio.create_task(_safe(
            getcontact_search(e164, token=cfg.get("getcontact_token", "")), "getcontact"
        )),
        "vk": asyncio.create_task(_safe(
            vk_user_search(e164), "vk"
        )),
    }
    return await _gather_tasks(tasks)


async def _search_email(q: str, cfg: dict) -> dict:
    from modules.email_lookup import hibp_check
    from modules.leakcheck import leakcheck_search

    tasks = {
        "hibp": asyncio.create_task(_safe(
            hibp_check(q), "hibp"
        )),
        "leakcheck": asyncio.create_task(_safe(
            leakcheck_search(q, api_key=cfg.get("leakcheck_key", "")), "leakcheck"
        )),
    }
    return await _gather_tasks(tasks)


async def _search_inn(q: str, qtype: str) -> dict:
    from modules.egrul import egrul_search

    tasks = {
        "egrul": asyncio.create_task(_safe(egrul_search(q), "egrul")),
    }
    return await _gather_tasks(tasks)


async def _search_domain(q: str) -> dict:
    from modules.domain_lookup import whois_lookup, dns_lookup

    # убираем схему если есть
    domain = re.sub(r'^https?://', '', q).split('/')[0].strip()

    tasks = {
        "whois": asyncio.create_task(_safe(whois_lookup(domain), "whois")),
        "dns": asyncio.create_task(_safe(dns_lookup(domain), "dns")),
    }
    return await _gather_tasks(tasks)


async def _search_ip(q: str) -> dict:
    from modules.domain_lookup import get_ip_geolocation

    tasks = {
        "geo": asyncio.create_task(_safe(get_ip_geolocation(q), "ip_geo")),
    }
    return await _gather_tasks(tasks)


async def _search_username(q: str, cfg: dict) -> dict:
    from modules.vk_lookup import vk_user_lookup
    from modules.telegram_lookup import tg_user_lookup
    from modules.ok_lookup import ok_user_lookup
    from modules.instagram_lookup import instagram_lookup
    from modules.twitter_lookup import twitter_lookup

    tasks = {
        "vk": asyncio.create_task(_safe(vk_user_lookup(q), "vk")),
        "tg": asyncio.create_task(_safe(tg_user_lookup(q), "tg")),
        "ok": asyncio.create_task(_safe(ok_user_lookup(q), "ok")),
        "instagram": asyncio.create_task(_safe(instagram_lookup(q), "instagram")),
        "twitter": asyncio.create_task(_safe(twitter_lookup(q), "twitter")),
    }
    return await _gather_tasks(tasks)


async def _search_fio(q: str, cfg: dict) -> dict:
    from modules.fio_lookup import fio_search

    parts = q.split()
    last = parts[0] if parts else ""
    first = parts[1] if len(parts) > 1 else ""
    middle = parts[2] if len(parts) > 2 else ""

    tasks = {
        "fio": asyncio.create_task(_safe(
            fio_search(
                first=first,
                last=last,
                middle=middle,
                leakcheck_key=cfg.get("leakcheck_key", ""),
                dehashed_email=cfg.get("dehashed_email", ""),
                dehashed_key=cfg.get("dehashed_key", ""),
                intelx_key=cfg.get("intelx_key", ""),
            ),
            "fio"
        )),
    }
    return await _gather_tasks(tasks)


async def _search_car(q: str) -> dict:
    from modules.car_lookup import car_check, normalize_plate

    plate = normalize_plate(q)
    tasks = {
        "car": asyncio.create_task(_safe(car_check(plate), "car")),
    }
    return await _gather_tasks(tasks)


async def _search_passport(q: str) -> dict:
    from modules.doc_lookup import check_passport

    parts = q.split()
    series = parts[0] if parts else q[:4]
    number = parts[1] if len(parts) > 1 else q[4:].strip()
    tasks = {
        "passport": asyncio.create_task(_safe(check_passport(series, number), "passport")),
    }
    return await _gather_tasks(tasks)


async def _search_cadastral(q: str) -> dict:
    from modules.address_lookup import rosreestr_lookup

    tasks = {
        "rosreestr": asyncio.create_task(_safe(rosreestr_lookup(q), "rosreestr")),
    }
    return await _gather_tasks(tasks)


async def _gather_tasks(tasks: dict) -> dict:
    results = {}
    done = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for key, result in zip(tasks.keys(), done):
        if isinstance(result, Exception):
            log.error("osint_search task %r упал: %s", key, result)
            results[key] = {"error": str(result)}
        else:
            results[key] = result
    return results
