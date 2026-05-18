"""
Maigret — поиск username по 3000+ сайтам.
Устанавливается через pip install maigret.
Docs: https://github.com/soxoj/maigret
"""
import asyncio
import json
import logging
import os
import tempfile

log = logging.getLogger(__name__)

# Топ сайтов для быстрого поиска. Полный скан (3000+) занимает ~5 минут.
# 500 покрывают самые популярные и быстрые сайты за ~30-60 секунд.
DEFAULT_TOP_SITES = 500


async def maigret_search(
    username: str,
    top_sites: int = DEFAULT_TOP_SITES,
    timeout: int = 90,
) -> dict:
    """
    Ищет username на top_sites самых популярных сайтах через Maigret.
    Возвращает список найденных аккаунтов с URL и категорией.
    """
    log.debug("maigret_search: %r top_sites=%d", username, top_sites)

    tmp = tempfile.mktemp(suffix=".json")
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-m", "maigret", username,
            "--json", tmp,
            "--timeout", "5",
            "--retries", "1",
            "--top-sites", str(top_sites),
            "--no-color",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            log.warning("maigret_search: timeout для %r", username)
            return {"error": "timeout", "found": 0, "results": []}

        if not os.path.exists(tmp):
            return {"found": 0, "results": []}

        with open(tmp, encoding="utf-8") as f:
            raw = json.load(f)

        results = []
        for site_name, entry in raw.items():
            status = entry.get("status", {})
            status_val = status.get("status", "") if isinstance(status, dict) else str(status)
            if status_val.lower() != "claimed":
                continue
            url = entry.get("url_user", entry.get("url", ""))
            category = ""
            site_info = entry.get("site", {})
            if isinstance(site_info, dict):
                category = site_info.get("category", "")
                tags = site_info.get("tags", [])
            else:
                tags = []
            results.append({
                "site":     site_name,
                "url":      url,
                "category": category,
                "tags":     tags[:3],
            })

        log.debug("maigret_search: найдено %d аккаунтов для %r", len(results), username)
        return {"found": len(results), "scanned": top_sites, "results": results}

    except FileNotFoundError:
        return {"error": "maigret не установлен (pip install maigret)"}
    except Exception as e:
        log.error("maigret_search: %s", e)
        return {"error": str(e), "found": 0, "results": []}
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def group_by_category(results: list[dict]) -> dict[str, list[dict]]:
    """Группирует результаты по категориям для удобного вывода."""
    groups: dict[str, list] = {}
    for r in results:
        cat = r.get("category") or "other"
        groups.setdefault(cat, []).append(r)
    return dict(sorted(groups.items()))
