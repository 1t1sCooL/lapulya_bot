from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.email_lookup import validate_email, hibp_check, email_domain_mx
from utils.formatter import kv, section, list_items, error_msg
import asyncio

router = Router()


@router.message(Command("email"))
async def cmd_email(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: <code>/email test@example.com</code>", parse_mode="HTML")
        return
    email = args[1].strip().lower()

    if not validate_email(email):
        await message.answer(error_msg(f"<code>{email}</code> не является корректным email"), parse_mode="HTML")
        return

    msg = await message.answer(f"🔍 Проверяю <code>{email}</code>...", parse_mode="HTML")

    hibp, mx = await asyncio.gather(hibp_check(email), email_domain_mx(email))

    text = f"📧 <b>OSINT: {email}</b>\n"

    # Базовая инфо
    basic = [
        kv("Email", email),
        kv("Домен", email.split("@")[-1]),
        kv("MX-серверы", ", ".join(mx) if mx else "не найдены"),
    ]
    text += section("Информация", basic)

    # HIBP
    if "error" in hibp:
        text += section("Утечки (HIBP)", [f"⚠️ {hibp['error']}"])
    elif hibp.get("breached"):
        count = hibp["count"]
        breach_lines = []
        for b in hibp["breaches"][:10]:
            classes = ", ".join(b["data_classes"][:4])
            breach_lines.append(
                f"  🔴 <b>{b['name']}</b> ({b['date']})\n"
                f"     Данные: <i>{classes}</i>\n"
                f"     Записей: {b['pwn_count']:,}\n"
            )
        text += section(f"Утечки (найдено: {count})", breach_lines)
    else:
        text += section("Утечки (HIBP)", ["✅ Email не найден в известных утечках"])

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
