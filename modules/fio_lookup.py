"""
FIO (ФИО) — агрегатор OSINT-поиска по имени/отчеству/фамилии.
Объединяет: LeakCheck, DeHashed, IntelX, VK, HH.ru.
"""
import asyncio
import logging

from modules.leakcheck import leakcheck_search
from modules.dehashed import dehashed_search
from modules.intelx import intelx_search
from modules.vk_lookup import vk_user_search
from modules.hh_lookup import hh_resume_search

log = logging.getLogger(__name__)

# Таблица транслитерации кириллица → латиница (ГОСТ Р 52535.1-2006 / ISO 9)
_TRANSLIT: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}


def transliterate_name(text: str) -> str:
    """Транслитерирует строку из кириллицы в латиницу."""
    result = []
    for ch in text.lower():
        result.append(_TRANSLIT.get(ch, ch))
    return "".join(result)


def generate_username_variants(first: str, last: str, middle: str = "") -> list[str]:
    """
    Генерирует варианты никнеймов из ФИО.
    Все варианты в транслите, нижний регистр.
    """
    f = transliterate_name(first)
    l = transliterate_name(last)
    m = transliterate_name(middle) if middle else ""
    f1 = f[:1]   # первая буква имени
    m1 = m[:1]   # первая буква отчества

    variants: list[str] = []

    # Основные паттерны
    variants.append(f"{l}.{f}")           # ivanov.ivan
    variants.append(f"{f}.{l}")           # ivan.ivanov
    variants.append(f"{l}_{f}")           # ivanov_ivan
    variants.append(f"{f}_{l}")           # ivan_ivanov
    variants.append(f"{l}{f1}")           # ivanova_i → ivanov_i
    variants.append(f"{f1}{l}")           # i_ivanov
    variants.append(f"{l}")              # ivanov
    if m1:
        variants.append(f"{l}_{f1}{m1}") # ivanov_ii

    # Убираем пустые, дубли, сортируем
    seen: set[str] = set()
    result: list[str] = []
    for v in variants:
        v = v.strip("._").lower()
        if v and v not in seen:
            seen.add(v)
            result.append(v)

    log.debug("generate_username_variants: %r → %d вариантов: %s", f"{last} {first}", len(result), result)
    return result


async def fio_search(
    first: str,
    last: str,
    middle: str = "",
    leakcheck_key: str = "",
    dehashed_email: str = "",
    dehashed_key: str = "",
    intelx_key: str = "",
) -> dict:
    """
    Параллельный OSINT-поиск по ФИО через все доступные источники.
    Возвращает агрегированный dict.
    """
    full_name = f"{last} {first}"
    if middle:
        full_name_full = f"{last} {first} {middle}"
    else:
        full_name_full = full_name

    log.debug("fio_search: старт поиска %r", full_name_full)

    username_variants = generate_username_variants(first, last, middle)

    # Строим список задач для asyncio.gather
    async def _leakcheck():
        log.debug("fio_search[leakcheck]: запрос %r", full_name)
        try:
            result = await leakcheck_search(full_name, leakcheck_key, "name")
            log.debug("fio_search[leakcheck]: найдено %d", result.get("found", 0))
            return result
        except Exception as e:
            log.error("fio_search[leakcheck]: ошибка %s", e)
            return {"error": str(e)}

    async def _dehashed():
        log.debug("fio_search[dehashed]: запрос %r", full_name)
        try:
            result = await dehashed_search(full_name, dehashed_email, dehashed_key, field="name")
            log.debug("fio_search[dehashed]: найдено %d", result.get("total", 0))
            return result
        except Exception as e:
            log.error("fio_search[dehashed]: ошибка %s", e)
            return {"error": str(e)}

    async def _intelx():
        log.debug("fio_search[intelx]: запрос %r", full_name_full)
        try:
            result = await intelx_search(full_name_full, intelx_key)
            log.debug("fio_search[intelx]: найдено %d", result.get("found", 0))
            return result
        except Exception as e:
            log.error("fio_search[intelx]: ошибка %s", e)
            return {"error": str(e)}

    async def _vk():
        log.debug("fio_search[vk]: запрос %r", f"{first} {last}")
        try:
            result = await vk_user_search(f"{first} {last}")
            log.debug("fio_search[vk]: найдено %d", result.get("found", 0))
            return result
        except Exception as e:
            log.error("fio_search[vk]: ошибка %s", e)
            return {"error": str(e)}

    async def _hh():
        log.debug("fio_search[hh]: запрос %r", full_name)
        try:
            result = await hh_resume_search(full_name)
            log.debug("fio_search[hh]: найдено %d", result.get("found", 0))
            return result
        except Exception as e:
            log.error("fio_search[hh]: ошибка %s", e)
            return {"error": str(e)}

    breach_lc, breach_dh, breach_ix, vk, hh = await asyncio.gather(
        _leakcheck(), _dehashed(), _intelx(), _vk(), _hh()
    )

    log.debug(
        "fio_search: завершено — lc=%s dh=%s ix=%s vk=%s hh=%s",
        "ok" if "error" not in breach_lc else "err",
        "ok" if "error" not in breach_dh else "err",
        "ok" if "error" not in breach_ix else "err",
        "ok" if "error" not in vk else "err",
        "ok" if "error" not in hh else "err",
    )

    return {
        "breach_lc": breach_lc,
        "breach_dh": breach_dh,
        "breach_ix": breach_ix,
        "vk": vk,
        "hh": hh,
        "username_variants": username_variants,
    }
