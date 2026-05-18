"""
Расшифровка хэшей через бесплатные rainbow-table сервисы.
Поддерживает MD5 (32 hex), SHA1 (40 hex), SHA256 (64 hex).
Пароль на сервер не отправляется — только хэш.
"""
import re
import asyncio
import logging
import httpx

log = logging.getLogger(__name__)

_HASH_TYPES = {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}


def detect_hash_type(h: str) -> str:
    h = h.strip().lower()
    if re.match(r'^[a-f0-9]+$', h):
        return _HASH_TYPES.get(len(h), "")
    return ""


async def crack_hash(hash_str: str) -> str | None:
    """
    Пробует расшифровать хэш через несколько бесплатных сервисов.
    Возвращает открытый текст или None.
    """
    h = hash_str.strip().lower()
    htype = detect_hash_type(h)
    if not htype:
        return None

    log.debug("crack_hash: %s (%s)", h[:10], htype)

    fns = []
    if htype in ("md5", "sha1", "sha256"):
        fns.append(_hashes_com(h, htype))
    if htype in ("md5", "sha1"):
        fns.append(_nitrxgen(h))
    if htype == "md5":
        fns.append(_md5_gromweb(h))

    for coro in asyncio.as_completed(fns):
        try:
            result = await coro
            if result:
                log.debug("crack_hash: взломан %s → %r", h[:10], result)
                return result
        except Exception:
            pass
    return None


async def crack_hashes_batch(hashes: list[str]) -> dict[str, str]:
    """
    Параллельный взлом списка хэшей.
    Возвращает {hash_lower: plaintext}.
    """
    unique = [h.strip().lower() for h in hashes if h and h.strip()]
    unique = list(dict.fromkeys(unique))   # убрать дубли
    if not unique:
        return {}
    results = await asyncio.gather(*[crack_hash(h) for h in unique], return_exceptions=True)
    out = {}
    for h, r in zip(unique, results):
        if isinstance(r, str) and r:
            out[h] = r
    return out


# ── Источники ──────────────────────────────────────────────────────────────

async def _hashes_com(h: str, htype: str) -> str | None:
    """hashes.com — бесплатный поиск хэшей, большая база, нет ключа."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://hashes.com/en/api/identifier",
                data={"hashvalue": h},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                d = r.json()
                if d.get("success") and d.get("plains"):
                    plain = d["plains"][0]
                    if plain and len(plain) < 200:
                        return plain
    except Exception:
        pass
    return None


async def _nitrxgen(h: str) -> str | None:
    """nitrxgen.net — бесплатная MD5/SHA1 rainbow table."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"https://www.nitrxgen.net/md5db/{h}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                t = r.text.strip()
                if t and len(t) < 200 and "\n" not in t:
                    return t
    except Exception:
        pass
    return None


async def _md5_gromweb(h: str) -> str | None:
    """md5.gromweb.com — MD5 reverse lookup."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                "https://md5.gromweb.com/",
                params={"md5": h},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code == 200:
                # Ответ — HTML, ищем строку с оригиналом
                if '"original"' in r.text:
                    import json
                    # Иногда отдаёт JSON fragment
                    m = re.search(r'"original"\s*:\s*"([^"]+)"', r.text)
                    if m:
                        return m.group(1)
    except Exception:
        pass
    return None


