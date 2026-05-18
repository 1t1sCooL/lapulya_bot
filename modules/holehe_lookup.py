"""
Holehe — проверяет на каких сервисах зарегистрирован email.
144 сервиса: Instagram, Spotify, Netflix, GitHub, Discord, Tinder и т.д.
Бесплатно, без ключей.
Docs: https://github.com/megadose/holehe
"""
import asyncio
import logging

log = logging.getLogger(__name__)

# Интересные сервисы — показываем первыми
PRIORITY_SERVICES = {
    "instagram", "twitter", "snapchat", "discord", "spotify", "github",
    "pinterest", "tumblr", "soundcloud", "lastfm", "flickr", "evernote",
    "adobe", "ebay", "amazon", "google", "yahoo", "protonmail", "patreon",
    "strava", "nike", "deliveroo", "blablacar", "venmo", "vsco",
    "odnoklassniki", "mail_ru", "rambler",
}


async def holehe_check(email: str, timeout: int = 60) -> dict:
    """
    Проверяет email на 144 сервисах через holehe.
    Возвращает список сервисов где email зарегистрирован.
    """
    log.debug("holehe_check: %r", email)
    try:
        import httpx
        from holehe.core import import_submodules, get_functions, launch_module

        modules = import_submodules("holehe.modules")
        functions = get_functions(modules)

        out: list[dict] = []

        async with httpx.AsyncClient() as client:
            tasks = [launch_module(func, email, client, out) for func in functions]
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
            except asyncio.TimeoutError:
                log.warning("holehe_check: timeout для %r", email)

        found = [r for r in out if r.get("exists")]
        not_found = [r for r in out if not r.get("exists") and not r.get("rateLimit")]

        # Собираем дополнительные данные где доступны
        extras = {}
        for r in found:
            name = r.get("name", "")
            info = {}
            if r.get("emailrecovery"):
                info["recovery_email"] = r["emailrecovery"]
            if r.get("phoneNumber"):
                info["phone"] = r["phoneNumber"]
            if r.get("others"):
                info["other"] = r["others"]
            if info:
                extras[name] = info

        log.debug("holehe_check: найдено %d сервисов из %d", len(found), len(out))
        return {
            "found":     len(found),
            "checked":   len(out),
            "services":  [r.get("name", "") for r in found],
            "domains":   {r.get("name", ""): r.get("domain", "") for r in found},
            "extras":    extras,
        }

    except ImportError:
        return {"error": "holehe не установлен (pip install holehe)"}
    except Exception as e:
        log.error("holehe_check: %s", e)
        return {"error": str(e)}
