"""
Загружает базу сайтов из sherlock-project и конвертирует в наш формат.
414 сайтов, постоянно обновляются сообществом.
pip install sherlock-project
"""
import json
import logging
import os

log = logging.getLogger(__name__)

# Сайты которые закрылись или дают постоянные false positive
_DEAD_SITES = {
    "Periscope",       # закрыт март 2021
    "Vine",            # закрыт 2017
    "Google+",         # закрыт 2019
    "Mixer",           # закрыт 2020
    "Parler",          # неоднократно закрывался
    "Gab",             # нестабильный
}

# Сайты с NSFW-контентом — часто дают false positive из-за изменений в UI
_UNRELIABLE_NSFW = {
    "Chaturbate", "RoyalCams", "LushStories", "APClips", "RocketTube",
    "xHamster", "Pornhub", "RedTube", "xVideos", "xNxx",
    "AdultFriendFinder", "YouPorn", "Cams",
}


def load_sherlock_sites(include_nsfw: bool = False) -> list[dict]:
    """
    Читает data.json из установленного sherlock-project и возвращает
    список сайтов в нашем формате (совместимо с username_lookup.py).
    include_nsfw=False — убирает ненадёжные NSFW-сайты с высоким % FP.
    """
    try:
        import importlib.resources as pkg
        try:
            ref = pkg.files("sherlock_project") / "resources" / "data.json"
            raw = ref.read_text(encoding="utf-8")
        except Exception:
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
    skipped_dead = 0
    skipped_nsfw = 0

    for name, info in data.items():
        if name == "$schema" or not isinstance(info, dict):
            continue

        # Фильтруем мёртвые сайты
        if name in _DEAD_SITES:
            skipped_dead += 1
            continue

        # Фильтруем NSFW с ненадёжной детекцией
        is_nsfw = info.get("isNSFW", False) or name in _UNRELIABLE_NSFW
        if is_nsfw and not include_nsfw:
            skipped_nsfw += 1
            continue

        url = info.get("url", "")
        if not url or "{}" not in url:
            continue

        error_type = info.get("errorType", "message")
        error_msg = info.get("errorMsg", "")
        regex = info.get("regexCheck")

        if error_type == "status_code":
            err_val = info.get("errorCode", 404)
        elif error_type == "message":
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
            "name":        name,
            "url":         url,
            "error_type":  error_type,
            "error_value": err_val,
            "regex":       regex,
            "is_nsfw":     is_nsfw,
        })

    log.debug(
        "sherlock_sites: загружено %d, пропущено мёртвых=%d nsfw=%d",
        len(sites), skipped_dead, skipped_nsfw,
    )
    return sites


def get_merged_sites(local_sites: list[dict]) -> list[dict]:
    """
    Объединяет локальную базу с базой Sherlock.
    Sherlock имеет приоритет (более свежие данные).
    """
    sherlock = load_sherlock_sites(include_nsfw=False)
    if not sherlock:
        return local_sites

    sherlock_names = {s["name"].lower() for s in sherlock}
    extra = [s for s in local_sites if s["name"].lower() not in sherlock_names]

    merged = sherlock + extra
    log.debug(
        "sherlock_sites: итого %d (sherlock=%d, local=%d)",
        len(merged), len(sherlock), len(extra),
    )
    return merged
