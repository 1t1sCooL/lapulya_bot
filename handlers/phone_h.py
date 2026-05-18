import asyncio
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.phone_lookup import parse_phone
from modules.leakcheck import leakcheck_search
from modules.dehashed import dehashed_search
from modules.intelx import intelx_search
from modules.getcontact import getcontact_search
from utils.formatter import kv, section, error_msg
import config

router = Router()
log = logging.getLogger(__name__)


@router.message(Command("phone"))
async def cmd_phone(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: <code>/phone +79001234567</code>", parse_mode="HTML"
        )
        return

    number = args[1].strip()
    result = parse_phone(number)

    if "error" in result:
        await message.answer(error_msg(result["error"]), parse_mode="HTML")
        return

    e164 = result.get("e164", number)
    log.debug("cmd_phone: пробив %r (e164=%r)", number, e164)

    msg = await message.answer(
        f"🔍 Пробиваю <code>{e164}</code>...", parse_mode="HTML"
    )

    # Запускаем все источники параллельно
    gc, lc, dh, ix = await asyncio.gather(
        getcontact_search(e164, config.GETCONTACT_TOKEN),
        leakcheck_search(e164, config.LEAKCHECK_API_KEY, "phone") if config.LEAKCHECK_API_KEY else _empty(),
        dehashed_search(e164, config.DEHASHED_EMAIL, config.DEHASHED_API_KEY, field="phone") if config.DEHASHED_API_KEY else _empty(),
        intelx_search(e164, config.INTELX_API_KEY) if config.INTELX_API_KEY else _empty(),
    )
    log.debug("cmd_phone: источники получены gc=%s lc=%s dh=%s ix=%s",
              "ok" if "error" not in gc else "err",
              "ok" if "error" not in lc else "err",
              "ok" if "error" not in dh else "err",
              "ok" if "error" not in ix else "err")

    valid_icon = "✅" if result["valid"] else "⚠️"
    text = f"📱 <b>OSINT: {e164}</b>\n"

    # Базовая инфо
    basic = [
        kv("Страна/Регион", result.get("region")),
        kv("Оператор", result.get("carrier") or "Неизвестно"),
        kv("Тип", result.get("number_type")),
        kv("Валидный", f"{valid_icon} {'Да' if result['valid'] else 'Нет'}"),
    ]
    text += section("Информация о номере", basic)

    # GetContact — имя из контактов
    if "error" not in gc and gc.get("name"):
        gc_lines = [kv("Имя в контактах", gc["name"])]
        if gc.get("tags"):
            gc_lines.append(kv("Теги", ", ".join(gc["tags"])))
        text += section("GetContact", gc_lines)
    elif "error" in gc and gc["error"] != "GETCONTACT_TOKEN не задан":
        text += section("GetContact", [f"⚠️ {gc['error']}\n"])

    # Breach-базы
    breach_lines = []
    for label, data in [("LeakCheck", lc), ("DeHashed", dh), ("IntelX", ix)]:
        if not data or "error" in data:
            if data and data.get("error") and "не задан" not in data["error"]:
                breach_lines.append(f"<b>{label}:</b> ⚠️ {data['error']}\n")
            continue
        count = data.get("found") or data.get("total") or 0
        if not count:
            continue
        breach_lines.append(f"<b>🔴 {label}</b> — найдено записей: <b>{count}</b>\n")
        records = data.get("results", [])[:5]
        for rec in records:
            parts = []
            if rec.get("name"):
                parts.append(f"🧑 <code>{rec['name']}</code>")
            if rec.get("email"):
                parts.append(f"📧 <code>{rec['email']}</code>")
            if rec.get("username"):
                parts.append(f"👤 <code>{rec['username']}</code>")
            if rec.get("password"):
                parts.append(f"🔑 <code>{rec['password']}</code>")
            src = rec.get("source") or rec.get("database") or rec.get("name", "")
            if src:
                parts.append(f"<i>({src})</i>")
            if parts:
                breach_lines.append("  🔸 " + " | ".join(parts) + "\n")

    if breach_lines:
        text += section("Базы утечек", breach_lines)
    elif config.LEAKCHECK_API_KEY or config.DEHASHED_API_KEY:
        text += section("Базы утечек", ["✅ Номер не найден в утечках\n"])

    if len(text) > 4000:
        text = text[:3980] + "\n\n<i>… обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


async def _empty() -> dict:
    return {}
