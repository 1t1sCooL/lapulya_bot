import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.leakcheck import leakcheck_search
from modules.intelx import intelx_search, intelx_phonebook
from modules.dehashed import dehashed_search
from modules.breachdirectory import breachdirectory_search
from modules.email_lookup import hibp_check
from modules.proxynova import proxynova_search
from modules.hudsonrock import hudsonrock_email, hudsonrock_username, hudsonrock_domain
import config

router = Router()

HELP_TEXT = (
    "<b>/breach</b> — поиск по базам утечек\n\n"
    "Использование:\n"
    "  <code>/breach email user@example.com</code>\n"
    "  <code>/breach phone +79001234567</code>\n"
    "  <code>/breach username johndoe</code>\n"
    "  <code>/breach domain example.com</code>\n"
    "  <code>/breach name Иванов Иван</code>\n"
    "  <code>/breach ip 1.2.3.4</code>\n\n"
    "Источники: LeakCheck · Dehashed · IntelX · BreachDirectory · HIBP"
)


@router.message(Command("breach"))
async def cmd_breach(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    query_type = parts[1].lower()
    query = parts[2].strip()

    valid_types = {"email", "phone", "username", "domain", "name", "ip"}
    if query_type not in valid_types:
        await message.answer(
            f"Неизвестный тип: <code>{query_type}</code>\n"
            f"Допустимые: {', '.join(sorted(valid_types))}",
            parse_mode="HTML",
        )
        return

    msg = await message.answer(
        f"🔍 Пробиваю <code>{query}</code> по базам утечек...",
        parse_mode="HTML",
    )

    # Запускаем все источники параллельно
    tasks = _build_tasks(query_type, query)
    results_raw = await asyncio.gather(*tasks.values(), return_exceptions=True)
    results = dict(zip(tasks.keys(), results_raw))

    text = _format_results(query, query_type, results)
    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


def _build_tasks(query_type: str, query: str) -> dict:
    tasks = {}

    if config.LEAKCHECK_API_KEY:
        lc_type = {
            "email": "email", "phone": "phone", "username": "username",
            "domain": "domain", "name": "name", "ip": "keyword",
        }.get(query_type, "auto")
        tasks["leakcheck"] = leakcheck_search(query, config.LEAKCHECK_API_KEY, lc_type)

    if config.DEHASHED_EMAIL and config.DEHASHED_API_KEY:
        dh_field = {
            "email": "email", "phone": "phone", "username": "username",
            "domain": "domain", "name": "name", "ip": "ip_address",
        }.get(query_type, "email")
        tasks["dehashed"] = dehashed_search(
            query, config.DEHASHED_EMAIL, config.DEHASHED_API_KEY, dh_field
        )

    if config.INTELX_API_KEY:
        if query_type == "domain":
            tasks["intelx_pb"] = intelx_phonebook(query, config.INTELX_API_KEY)
        tasks["intelx"] = intelx_search(query, config.INTELX_API_KEY)

    if config.RAPIDAPI_KEY and query_type in ("email", "username"):
        tasks["breachdir"] = breachdirectory_search(query, config.RAPIDAPI_KEY)

    if config.HIBP_API_KEY and query_type == "email":
        tasks["hibp"] = hibp_check(query)

    # Proxynova COMB — бесплатно, без ключа, для email/username/name
    if query_type in ("email", "username", "name"):
        tasks["proxynova"] = proxynova_search(query)

    # Hudson Rock Cavalier — инфостилеры, бесплатно
    if query_type == "email":
        tasks["hudsonrock"] = hudsonrock_email(query)
    elif query_type == "username":
        tasks["hudsonrock"] = hudsonrock_username(query)
    elif query_type == "domain":
        tasks["hudsonrock"] = hudsonrock_domain(query)

    return tasks


def _format_results(query: str, query_type: str, results: dict) -> str:
    lines = [f"🗄 <b>Пробив: <code>{query}</code></b> [{query_type}]\n"]
    any_found = False

    # ── LeakCheck ────────────────────────────────────────────────────
    lc = results.get("leakcheck")
    if isinstance(lc, dict) and "error" not in lc:
        count = lc.get("found", 0)
        any_found = any_found or count > 0
        lines.append(f"\n<b>🔴 LeakCheck</b> — найдено записей: <b>{count}</b>")
        for rec in lc.get("results", [])[:10]:
            row = _fmt_leak_record(rec)
            if row:
                lines.append(row)
    elif isinstance(lc, dict):
        lines.append(f"\n<b>LeakCheck:</b> ⚠️ {lc['error']}")

    # ── Dehashed ─────────────────────────────────────────────────────
    dh = results.get("dehashed")
    if isinstance(dh, dict) and "error" not in dh:
        total = dh.get("total", 0)
        any_found = any_found or total > 0
        lines.append(f"\n<b>🔴 Dehashed</b> — всего записей: <b>{total:,}</b>")
        for rec in dh.get("results", [])[:10]:
            row = _fmt_dehashed_record(rec)
            if row:
                lines.append(row)
    elif isinstance(dh, dict):
        lines.append(f"\n<b>Dehashed:</b> ⚠️ {dh['error']}")

    # ── IntelX ───────────────────────────────────────────────────────
    ix = results.get("intelx")
    if isinstance(ix, dict) and "error" not in ix:
        count = ix.get("found", 0)
        any_found = any_found or count > 0
        lines.append(f"\n<b>🔴 IntelligenceX</b> — найдено источников: <b>{count}</b>")
        for rec in ix.get("results", [])[:8]:
            if rec.get("name"):
                lines.append(
                    f"  📄 {rec['name'][:60]} "
                    f"<i>({rec.get('media', '')}, {rec.get('date', '')})</i>"
                )
    elif isinstance(ix, dict):
        lines.append(f"\n<b>IntelX:</b> ⚠️ {ix['error']}")

    # ── IntelX Phonebook (для domain) ─────────────────────────────────
    ixpb = results.get("intelx_pb")
    if isinstance(ixpb, dict) and "error" not in ixpb:
        emails = ixpb.get("emails", [])
        if emails:
            any_found = True
            lines.append(f"\n<b>📒 IntelX Phonebook</b> — emails на домене: <b>{len(emails)}</b>")
            for e in emails[:15]:
                lines.append(f"  • <code>{e}</code>")
    elif isinstance(ixpb, dict):
        lines.append(f"\n<b>IntelX PB:</b> ⚠️ {ixpb['error']}")

    # ── BreachDirectory ───────────────────────────────────────────────
    bd = results.get("breachdir")
    if isinstance(bd, dict) and "error" not in bd:
        if bd.get("found"):
            any_found = True
            lines.append(f"\n<b>🔴 BreachDirectory</b> — найдено хэшей: <b>{bd.get('count', 0)}</b>")
            for rec in bd.get("results", [])[:5]:
                parts = []
                if rec.get("hash"):
                    parts.append(f"hash: <code>{rec['hash'][:40]}…</code>")
                if rec.get("sources"):
                    parts.append("источники: " + ", ".join(rec["sources"][:3]))
                if parts:
                    lines.append("  🔸 " + " | ".join(parts))
        else:
            lines.append("\n<b>BreachDirectory:</b> ✅ не найдено")
    elif isinstance(bd, dict):
        lines.append(f"\n<b>BreachDirectory:</b> ⚠️ {bd['error']}")

    # ── HIBP ─────────────────────────────────────────────────────────
    hibp = results.get("hibp")
    if isinstance(hibp, dict) and "error" not in hibp:
        if hibp.get("breached"):
            any_found = True
            lines.append(f"\n<b>🔴 HaveIBeenPwned</b> — утечек: <b>{hibp.get('count', 0)}</b>")
            for b in hibp.get("breaches", [])[:5]:
                classes = ", ".join(b.get("data_classes", [])[:3])
                lines.append(f"  🔸 <b>{b['name']}</b> ({b['date']}) — {classes}")
        else:
            lines.append("\n<b>HIBP:</b> ✅ не найдено в известных утечках")
    elif isinstance(hibp, dict):
        lines.append(f"\n<b>HIBP:</b> ⚠️ {hibp['error']}")

    # ── Proxynova COMB ────────────────────────────────────────────────
    pn = results.get("proxynova")
    if isinstance(pn, dict) and "error" not in pn:
        count = pn.get("found", 0)
        if count > 0:
            any_found = True
            lines.append(f"\n<b>🔴 Proxynova COMB</b> — найдено записей: <b>{count:,}</b>")
            for rec in pn.get("results", [])[:8]:
                login = rec.get("login", "")
                pwd = rec.get("password", "")
                if pwd:
                    lines.append(f"  🔸 <code>{login}</code> : <code>{pwd}</code>")
                else:
                    lines.append(f"  🔸 <code>{login}</code>")
        else:
            lines.append("\n<b>Proxynova COMB:</b> ✅ не найдено")
    elif isinstance(pn, dict):
        lines.append(f"\n<b>Proxynova:</b> ⚠️ {pn['error']}")

    # ── Hudson Rock ───────────────────────────────────────────────────
    hr = results.get("hudsonrock")
    if isinstance(hr, dict) and "error" not in hr and hr.get("found", 0) > 0:
        any_found = True
        lines.append(f"\n<b>🚨 Hudson Rock</b> — заражённых машин: <b>{hr['found']}</b>")
        for s in hr.get("stealers", [])[:3]:
            lines.append(
                f"  🦠 {s['date']} | {s['computer'] or '?'} | {s['total_services']} сервисов"
            )
    elif isinstance(hr, dict) and "error" in hr:
        lines.append(f"\n<b>HudsonRock:</b> ⚠️ {hr['error']}")

    if not any(k in results for k in ("leakcheck", "dehashed", "intelx", "breachdir", "hibp", "proxynova", "hudsonrock")):
        lines.append("\n⚠️ Все источники недоступны.")

    if not any_found:
        lines.append("\n\n✅ <i>По данному запросу утечек не обнаружено.</i>")
    else:
        lines.append("\n\n<i>⚠️ Данные получены из публично известных утечек.</i>")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3980] + "\n\n<i>... обрезано</i>"
    return text


def _fmt_leak_record(rec: dict) -> str:
    parts = []
    if rec.get("email"):
        parts.append(f"📧 <code>{rec['email']}</code>")
    if rec.get("username"):
        parts.append(f"👤 <code>{rec['username']}</code>")
    if rec.get("password"):
        parts.append(f"🔑 <code>{rec['password']}</code>")
    elif rec.get("password_hash"):
        parts.append(f"🔒 <code>{rec['password_hash'][:40]}</code>")
    if rec.get("phone"):
        parts.append(f"📱 <code>{rec['phone']}</code>")
    if rec.get("source"):
        parts.append(f"<i>({rec['source']})</i>")
    return "  🔸 " + " | ".join(parts) if parts else ""


def _fmt_dehashed_record(rec: dict) -> str:
    parts = []
    if rec.get("email"):
        parts.append(f"📧 <code>{rec['email']}</code>")
    if rec.get("username"):
        parts.append(f"👤 <code>{rec['username']}</code>")
    if rec.get("password"):
        parts.append(f"🔑 <code>{rec['password']}</code>")
    elif rec.get("hashed_password"):
        parts.append(f"🔒 <code>{rec['hashed_password'][:40]}</code>")
    if rec.get("name"):
        parts.append(f"🧑 <code>{rec['name']}</code>")
    if rec.get("phone"):
        parts.append(f"📱 <code>{rec['phone']}</code>")
    if rec.get("ip"):
        parts.append(f"🖥 <code>{rec['ip']}</code>")
    if rec.get("database"):
        parts.append(f"<i>({rec['database']})</i>")
    return "  🔸 " + " | ".join(parts) if parts else ""
