import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.fio_lookup import fio_search
from utils.formatter import kv, section, list_items, error_msg
import config

router = Router()
log = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>/fio</b> — OSINT-поиск по ФИО\n\n"
    "Использование:\n"
    "  <code>/fio Иванов Иван Иванович</code>\n"
    "  <code>/fio Иванов Иван</code>\n\n"
    "Источники: LeakCheck · DeHashed · IntelX · VK · HH.ru"
)


@router.message(Command("fio"))
async def cmd_fio(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    parts = args[1].strip().split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ Укажи минимум Фамилию и Имя.\n" + HELP_TEXT,
            parse_mode="HTML",
        )
        return

    last = parts[0]
    first = parts[1]
    middle = parts[2] if len(parts) >= 3 else ""

    display_name = f"{last} {first}" + (f" {middle}" if middle else "")
    log.debug("cmd_fio: запрос %r от user_id=%s", display_name, message.from_user.id if message.from_user else "?")

    msg = await message.answer(
        f"🔍 Ищу <b>{display_name}</b> по всем источникам...",
        parse_mode="HTML",
    )

    log.debug("cmd_fio: запуск fio_search для %r", display_name)
    results = await fio_search(
        first=first,
        last=last,
        middle=middle,
        leakcheck_key=config.LEAKCHECK_API_KEY,
        dehashed_email=config.DEHASHED_EMAIL,
        dehashed_key=config.DEHASHED_API_KEY,
        intelx_key=config.INTELX_API_KEY,
    )
    log.debug("cmd_fio: поиск завершён для %r", display_name)

    text = f"👤 <b>OSINT: {display_name}</b>\n"
    text += _fmt_breach(results)
    text += _fmt_vk(results.get("vk", {}))
    text += _fmt_hh(results.get("hh", {}))
    text += _fmt_variants(results.get("username_variants", []))

    if len(text) > 4000:
        text = text[:3980] + "\n\n<i>… обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


def _fmt_breach(results: dict) -> str:
    lc = results.get("breach_lc", {})
    dh = results.get("breach_dh", {})
    ix = results.get("breach_ix", {})

    lines = []

    # LeakCheck
    if isinstance(lc, dict) and "error" not in lc and lc.get("found", 0) > 0:
        lines.append(f"<b>🔴 LeakCheck</b> — {lc['found']} записей\n")
        for rec in lc.get("results", [])[:5]:
            parts = []
            if rec.get("email"):
                parts.append(f"📧 <code>{rec['email']}</code>")
            if rec.get("username"):
                parts.append(f"👤 <code>{rec['username']}</code>")
            if rec.get("phone"):
                parts.append(f"📱 <code>{rec['phone']}</code>")
            if rec.get("source"):
                parts.append(f"<i>({rec['source']})</i>")
            if parts:
                lines.append("  🔸 " + " | ".join(parts) + "\n")
    elif isinstance(lc, dict) and "error" in lc:
        lines.append(f"<b>LeakCheck:</b> ⚠️ {lc['error']}\n")

    # DeHashed
    if isinstance(dh, dict) and "error" not in dh and dh.get("total", 0) > 0:
        lines.append(f"<b>🔴 DeHashed</b> — {dh['total']:,} записей\n")
        for rec in dh.get("results", [])[:5]:
            parts = []
            if rec.get("email"):
                parts.append(f"📧 <code>{rec['email']}</code>")
            if rec.get("username"):
                parts.append(f"👤 <code>{rec['username']}</code>")
            if rec.get("phone"):
                parts.append(f"📱 <code>{rec['phone']}</code>")
            if rec.get("database"):
                parts.append(f"<i>({rec['database']})</i>")
            if parts:
                lines.append("  🔸 " + " | ".join(parts) + "\n")
    elif isinstance(dh, dict) and "error" in dh:
        lines.append(f"<b>DeHashed:</b> ⚠️ {dh['error']}\n")

    # IntelX
    if isinstance(ix, dict) and "error" not in ix and ix.get("found", 0) > 0:
        lines.append(f"<b>🔴 IntelX</b> — {ix['found']} источников\n")
        for rec in ix.get("results", [])[:5]:
            if rec.get("name"):
                lines.append(f"  📄 {rec['name'][:60]} <i>({rec.get('media', '')})</i>\n")
    elif isinstance(ix, dict) and "error" in ix:
        lines.append(f"<b>IntelX:</b> ⚠️ {ix['error']}\n")

    if not lines:
        lines.append("✅ <i>Утечек не обнаружено</i>\n")

    return section("Базы утечек", lines)


def _fmt_vk(vk: dict) -> str:
    if not vk or "error" in vk:
        err = vk.get("error", "") if vk else ""
        if err:
            return section("VK", [f"⚠️ {err}\n"])
        return ""

    items = vk.get("results", [])
    if not items:
        return section("VK", ["✅ Профили не найдены\n"])

    lines = [f"Найдено профилей: <b>{vk.get('found', len(items))}</b>\n"]
    for u in items[:8]:
        lock = "🔒" if u.get("is_closed") else "🔓"
        city = f", {u['city']}" if u.get("city") else ""
        bdate = f", {u['bdate']}" if u.get("bdate") else ""
        fol = f", {u['followers']} подп." if u.get("followers") else ""
        lines.append(
            f"  {lock} <a href='{u['url']}'>{u['name']}</a>"
            f"<i>{city}{bdate}{fol}</i>\n"
        )
    return section("VK", lines)


def _fmt_hh(hh: dict) -> str:
    if not hh or "error" in hh:
        err = hh.get("error", "") if hh else ""
        if err:
            return section("HH.ru", [f"⚠️ {err}\n"])
        return ""

    items = hh.get("results", [])
    if not items:
        return section("HH.ru", ["✅ Резюме не найдены\n"])

    lines = [f"Найдено резюме: <b>{hh.get('found', len(items))}</b>\n"]
    for r in items[:5]:
        area = f", {r['area']}" if r.get("area") else ""
        age = f", {r['age']} лет" if r.get("age") else ""
        url = r.get("url", "")
        title = r.get("title", "Без названия")[:60]
        if url:
            lines.append(f"  💼 <a href='{url}'>{title}</a><i>{area}{age}</i>\n")
        else:
            lines.append(f"  💼 {title}<i>{area}{age}</i>\n")
    return section("HH.ru", lines)


def _fmt_variants(variants: list[str]) -> str:
    if not variants:
        return ""
    lines = ["Используй с <code>/user &lt;ник&gt;</code>:\n"]
    lines.append(list_items(variants))
    return section("Username-варианты (транслит)", lines)
