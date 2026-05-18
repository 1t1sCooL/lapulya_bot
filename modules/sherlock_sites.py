"""
Загружает базу сайтов из sherlock-project и конвертирует в наш формат.
414 сайтов, постоянно обновляются сообществом.
pip install sherlock-project
"""
import json
import logging
import os

log = logging.getLogger(__name__)


def load_sherlock_sites() -> list[dict]:
    """
    Читает data.json из установленного sherlock-project и возвращает
    список сайтов в нашем формате (совместимо с username_lookup.py).
    """
    try:
        # Находим data.json через пакет
        import importlib.resources as pkg
        try:
            # Python 3.9+
            ref = pkg.files("sherlock_project") / "resources" / "data.json"
            raw = ref.read_text(encoding="utf-8")
        except Exception:
            # Fallback — ищем рядом с __init__.py
            import sherlock_project
            base = os.path.dirname(sherlock_project.__file__)
            path = os.path.join(base, "resources", "data.json")
            with open(path, encoding="utf-8") as f:
                raw = f.read()

        data = json.loads(raw)
    except Exception as e:
        log.warning("sherlock_sites: не удалось загрузить data.json: %s", e)
        return []

    sites = []
    for name, info in data.items():
        if name == "$schema" or not isinstance(info, dict):
            continue

        url = info.get("url", "")
        if not url or "{}" not in url:
            continue

        error_type = info.get("errorType", "message")
        error_msg = info.get("errorMsg", "")
        regex = info.get("regexCheck")

        # Конвертируем тип ошибки
        if error_type == "status_code":
            err_val = info.get("errorCode", 404)
        elif error_type == "message":
            # errorMsg может быть строкой или списком
            if isinstance(error_msg, list):
                err_val = error_msg[0] if error_msg else ""
            else:
                err_val = error_msg
        elif error_type == "response_url":
            err_val = info.get("errorUrl", "")
            error_type = "response_url"
        else:
            continue

        sites.append({
            "name":       name,
            "url":        url,
            "error_type": error_type,
            "error_value": err_val,
            "regex":      regex,
        })

    log.debug("sherlock_sites: загружено %d сайтов", len(sites))
    return sites


def get_merged_sites(local_sites: list[dict]) -> list[dict]:
    """
    Объединяет локальную базу с базой Sherlock.
    Sherlock имеет приоритет (более свежие данные).
    """
    sherlock = load_sherlock_sites()
    if not sherlock:
        return local_sites

    # Индекс по имени
    sherlock_names = {s["name"].lower() for s in sherlock}
    # Добавляем локальные сайты которых нет в Sherlock
    extra = [s for s in local_sites if s["name"].lower() not in sherlock_names]

    merged = sherlock + extra
    log.debug("sherlock_sites: итого %d сайтов (sherlock=%d, local=%d)", len(merged), len(sherlock), len(extra))
    return merged
