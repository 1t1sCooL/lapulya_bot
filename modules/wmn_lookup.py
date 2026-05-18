"""
WhatsMyName — поиск username по 1500+ сайтам.
Использует ПОЗИТИВНУЮ верификацию (строка должна ПРИСУТСТВОВАТЬ на странице).
Это надёжнее Sherlock, который ищет отсутствие строки ошибки.
Данные: https://github.com/WebBreacher/WhatsMyName
"""
import asyncio
import json
import logging
import re
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

WMN_DATA_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"

_WMN_CACHE: list[dict] | None = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
}


async def _load_wmn_sites() -> list[dict]:
    global _WMN_CACHE
    if _WMN_CACHE is not None:
        return _WMN_CACHE
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(WMN_DATA_URL)
            data = r.json()
        sites = [
            s for s in data.get("sites", [])
            if s.get("valid", True) and s.get("uri_check") and "{account}" in s["uri_check"]
        ]
        _WMN_CACHE = sites
        log.debug("wmn: загружено %d сайтов", len(sites))
        return sites
    except Exception as e:
        log.error("wmn: не удалось загрузить данные: %s", e)
        return []


async def _check_wmn_site(client: httpx.AsyncClient, site: dict, username: str) -> dict | None:
    url = site["uri_check"].replace("{account}", username)
    e_code = site.get("e_code", 200)
    e_string = site.get("e_string", "")
    m_string = site.get("m_string", "")
    regex = site.get("uri_check_regex", "")

    try:
        r = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=REQUEST_TIMEOUT)

        # Позитивная проверка: статус + строка должны присутствовать
        if r.status_code != e_code:
            return None

        # Если есть строка "не найден" и она есть на странице — пропускаем
        if m_string and m_string.lower() in r.text.lower():
            return None

        # Позитивная строка должна быть на странице
        if e_string and e_string.lower() not in r.text.lower():
            return None

        # Дополнительно: username должен быть на странице
        if username.lower() not in r.text.lower():
            return None

        return {
            "site":     site.get("name", ""),
            "url":      url,
            "category": site.get("category", ""),
        }
    except Exception:
        return None


async def wmn_search(username: str, max_concurrent: int = 40) -> dict:
    """
    Ищет username на 1500+ сайтах через WhatsMyName с позитивной верификацией.
    """
    log.debug("wmn_search: %r", username)
    sites = await _load_wmn_sites()
    if not sites:
        return {"error": "Не удалось загрузить базу WhatsMyName", "found": 0, "results": []}

    # Фильтр по regex если есть
    filtered = []
    for s in sites:
        rx = s.get("uri_check_regex")
        if rx:
            try:
                if not re.match(rx, username):
                    continue
            except Exception:
                pass
        filtered.append(s)

    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def bounded(site):
        async with semaphore:
            return await _check_wmn_site(client, site, username)

    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=60, max_keepalive_connections=20),
    ) as client:
        tasks = [bounded(s) for s in filtered]
        raw = await asyncio.gather(*tasks, return_exceptions=True)

    for r in raw:
        if isinstance(r, dict):
            results.append(r)

    log.debug("wmn_search: найдено %d из %d сайтов", len(results), len(filtered))
    return {
        "found":   len(results),
        "scanned": len(filtered),
        "results": sorted(results, key=lambda x: x["site"].lower()),
    }
