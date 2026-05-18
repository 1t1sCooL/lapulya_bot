import asyncio
import re
import httpx
from typing import AsyncIterator
from modules.sites_data import SITES
from config import REQUEST_TIMEOUT

# Объединяем с базой Sherlock при первом вызове
_ALL_SITES: list[dict] | None = None

def _get_sites() -> list[dict]:
    global _ALL_SITES
    if _ALL_SITES is None:
        try:
            from modules.sherlock_sites import get_merged_sites
            _ALL_SITES = get_merged_sites(SITES)
        except Exception:
            _ALL_SITES = SITES
    return _ALL_SITES

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
}


def filter_sites_by_regex(username: str) -> list[dict]:
    """Отфильтровываем сайты, чьи regex username не проходит."""
    valid = []
    for site in _get_sites():
        pattern = site.get("regex")
        if pattern and not re.match(pattern, username):
            continue
        valid.append(site)
    return valid


async def _check_one(
    client: httpx.AsyncClient,
    site: dict,
    username: str,
) -> dict | None:
    url = site["url"].format(username)
    error_type = site["error_type"]
    error_value = site["error_value"]

    try:
        r = await client.get(
            url,
            headers=HEADERS,
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT,
        )

        found = False

        if error_type == "status_code":
            found = r.status_code != error_value and r.status_code < 400

        elif error_type == "message":
            found = r.status_code < 400 and str(error_value) not in r.text
            # Доп. верификация: username должен реально присутствовать на странице
            if found:
                text_lower = r.text.lower()
                uname_lower = username.lower()
                found = uname_lower in text_lower

        elif error_type == "response_url":
            final_url = str(r.url)
            found = r.status_code < 400 and str(error_value) not in final_url
            # Для response_url тоже проверяем наличие username на странице
            if found:
                found = username.lower() in r.text.lower()

        if found:
            return {
                "site":       site["name"],
                "url":        url,
                "confidence": "high" if error_type == "status_code" else "medium",
            }

    except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
        pass
    except Exception:
        pass

    return None


async def username_search(
    username: str,
    max_concurrent: int = 30,
) -> list[dict]:
    """Проверяет username по всем сайтам, возвращает список найденных."""
    sites = filter_sites_by_regex(username)
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def bounded(site):
        async with semaphore:
            return await _check_one(client, site, username)

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    ) as client:
        tasks = [bounded(s) for s in sites]
        raw = await asyncio.gather(*tasks, return_exceptions=True)

    for r in raw:
        if isinstance(r, dict):
            results.append(r)

    return sorted(results, key=lambda x: x["site"].lower())


async def username_search_stream(
    username: str,
    max_concurrent: int = 30,
) -> AsyncIterator[dict]:
    """Стриминговая версия — yield результата по мере нахождения."""
    sites = filter_sites_by_regex(username)
    semaphore = asyncio.Semaphore(max_concurrent)
    queue: asyncio.Queue = asyncio.Queue()

    async def worker(site):
        async with semaphore:
            result = await _check_one(client, site, username)
            await queue.put(result)

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    ) as client:
        tasks = [asyncio.create_task(worker(s)) for s in sites]
        done_count = 0
        total = len(tasks)

        while done_count < total:
            item = await queue.get()
            done_count += 1
            if item is not None:
                yield item


def site_count() -> int:
    return len(_get_sites())
