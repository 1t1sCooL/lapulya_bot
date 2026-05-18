import asyncio
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.email_lookup import validate_email, hibp_check, email_domain_mx
from modules.leakcheck import leakcheck_public
from modules.hudsonrock import hudsonrock_email
from modules.proxynova import proxynova_search
from utils.formatter import kv, section, list_items, error_msg
import config

router = Router()
log = logging.getLogger(__name__)


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
    log.debug("cmd_email: %r", email)

    hibp, mx, lc_pub, hr, pn = await asyncio.gather(
        hibp_check(email),
        email_domain_mx(email),
        leakcheck_public(email),
        hudsonrock_email(email),
        proxynova_search(email),
    )

    text = f"📧 <b>OSINT: {email}</b>\n"

    # Базовая инфо
    basic = [
        kv("Домен", email.split("@")[-1]),
        kv("MX-серверы", ", ".join(mx[:3]) if mx else "не найдены"),
    ]
    text += section("Информация", basic)

    # LeakCheck public (без ключа — список источников)
    if "error" not in lc_pub and lc_pub.get("found", 0) > 0:
        sources = lc_pub.get("sources", [])
        src_lines = [f"Найдено в <b>{lc_pub['found']:,}</b> записях из {len(sources)} источников:\n"]
        for s in sources[:15]:
            date = f" ({s['date']})" if s.get("date") else ""
            src_lines.append(f"  🔸 {s['name']}{date}\n")
        text += section("LeakCheck (источники)", src_lines)

    # Proxynova COMB
    if "error" not in pn and pn.get("found", 0) > 0:
        pn_lines = [f"Найдено в COMB: <b>{pn['found']:,}</b> записей\n"]
        for rec in pn.get("results", [])[:5]:
            pwd = f" : <code>{rec['password']}</code>" if rec.get("password") else ""
            pn_lines.append(f"  🔸 <code>{rec['login']}</code>{pwd}\n")
        text += section("Proxynova COMB", pn_lines)

    # Hudson Rock — инфостилеры
    if "error" not in hr and hr.get("found", 0) > 0:
        hr_lines = [f"⚠️ Email найден на <b>{hr['found']}</b> заражённых компьютерах!\n"]
        for s in hr.get("stealers", [])[:3]:
            hr_lines.append(
                f"  🦠 <b>{s['date']}</b> — {s['computer'] or 'Unknown PC'}\n"
                f"     ОС: {s['os'] or '?'} | Сервисов: {s['total_services']}\n"
            )
        if hr.get("total_user", 0):
            hr_lines.append(f"  Всего учёток на заражённых машинах: <b>{hr['total_user']:,}</b>\n")
        text += section("🚨 Hudson Rock (инфостилеры)", hr_lines)

    # HIBP
    if "error" not in hibp:
        if hibp.get("breached"):
            breach_lines = []
            for b in hibp["breaches"][:8]:
                classes = ", ".join(b["data_classes"][:3])
                breach_lines.append(f"  🔴 <b>{b['name']}</b> ({b['date']}) — {classes}\n")
            text += section(f"HIBP — утечек: {hibp['count']}", breach_lines)
        else:
            text += section("HIBP", ["✅ Не найдено в известных утечках\n"])

    if len(text) > 4000:
        text = text[:3980] + "\n<i>… обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
