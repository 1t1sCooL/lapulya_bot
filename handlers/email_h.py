import asyncio
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.email_lookup import validate_email, hibp_check, email_domain_mx
from modules.leakcheck import leakcheck_public
from modules.hudsonrock import hudsonrock_email
from modules.proxynova import proxynova_search
from modules.xposedornot import xon_check_email
from modules.scylla import scylla_search
from modules.cassandra import cassandra_search
from modules.stopforumspam import sfs_check
from modules.hashcrack import crack_hashes_batch, detect_hash_type
from modules.emailrep import emailrep_check
from modules.ipqualityscore import ipqs_email
from modules.holehe_lookup import holehe_check
from utils.formatter import kv, section, list_items, error_msg
import config

router = Router()
log = logging.getLogger(__name__)


def _split_msg(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts


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

    hibp, mx, lc_pub, hr, pn, xon, sfs, erep, ipqs, holehe = await asyncio.gather(
        hibp_check(email),
        email_domain_mx(email),
        leakcheck_public(email),
        hudsonrock_email(email),
        proxynova_search(email),
        xon_check_email(email),
        sfs_check(email, "email"),
        emailrep_check(email, config.EMAILREP_API_KEY),
        ipqs_email(email, config.IPQS_API_KEY) if config.IPQS_API_KEY else asyncio.sleep(0, result={}),
        holehe_check(email),
    )
    sc = {"found": 0, "results": []}   # scylla.sh offline
    cas = {"found": 0, "results": []}  # cassandra.sh offline
    cracked = {}

    text = f"📧 <b>OSINT: {email}</b>\n"

    # Базовая инфо
    rep_emoji = {"high": "🟢", "medium": "🟡", "low": "🟠", "none": "🔴"}.get(
        erep.get("reputation", ""), "⚪"
    ) if "error" not in erep else "⚪"
    basic = [
        kv("Домен", email.split("@")[-1]),
        kv("MX-серверы", ", ".join(mx[:3]) if mx else "не найдены"),
        kv("Репутация", f"{rep_emoji} {erep.get('reputation', '?')}") if "error" not in erep else "",
        kv("Одноразовый", "Да ⚠️" if erep.get("disposable") else "Нет") if "error" not in erep else "",
        kv("Утечки (EmailRep)", "Да 🔴" if erep.get("credentials_leaked") else "Нет") if "error" not in erep else "",
        kv("Соцсети", ", ".join(erep.get("profiles", [])[:5])) if erep.get("profiles") else "",
    ]
    # IPQS email score
    if isinstance(ipqs, dict) and "error" not in ipqs and ipqs:
        fs = ipqs.get("fraud_score", 0)
        fs_emoji = "🔴" if fs >= 75 else ("🟠" if fs >= 40 else "🟢")
        basic += [
            kv("Фрод-скор (IPQS)", f"{fs_emoji} {fs}/100"),
            kv("Утечки (IPQS)", "Да 🔴" if ipqs.get("leaked") else "Нет"),
            kv("Спам-ловушка", "Да ⚠️" if ipqs.get("spam_trap") else "Нет") if ipqs.get("spam_trap") else "",
            kv("Доставляемость", ipqs.get("deliverability", "")),
        ]
    text += section("Информация", [b for b in basic if b])

    # Holehe — на каких сервисах зарегистрирован email
    if isinstance(holehe, dict) and "error" not in holehe and holehe.get("found", 0) > 0:
        svcs = holehe.get("services", [])
        domains = holehe.get("domains", {})
        extras = holehe.get("extras", {})
        checked = holehe.get("checked", 0)

        # Иконки для популярных сервисов
        icons = {
            "instagram": "📸", "twitter": "🐦", "snapchat": "👻",
            "discord": "🎮", "spotify": "🎵", "github": "💻",
            "google": "🔍", "amazon": "📦", "ebay": "🛒",
            "patreon": "💰", "pinterest": "📌", "tumblr": "✏️",
            "adobe": "🎨", "nike": "👟", "strava": "🚴",
            "soundcloud": "🎧", "lastfm": "🎼", "flickr": "📷",
            "mail_ru": "📧", "odnoklassniki": "🤝", "rambler": "📧",
            "deliveroo": "🍕", "blablacar": "🚗", "venmo": "💸",
        }

        h_lines = [f"Зарегистрирован на <b>{len(svcs)}</b> из {checked} проверенных сервисов:\n"]
        for name in svcs:
            icon = icons.get(name, "🔹")
            domain = domains.get(name, "")
            extra_info = ""
            if name in extras:
                ex = extras[name]
                if ex.get("recovery_email"):
                    extra_info = f" → резерв: <code>{ex['recovery_email']}</code>"
                elif ex.get("phone"):
                    extra_info = f" → тел: <code>{ex['phone']}</code>"
            h_lines.append(f"  {icon} <b>{domain or name}</b>{extra_info}\n")
        text += section(f"🌐 Holehe (аккаунты на сервисах)", h_lines)

    # Scylla.sh — реальные записи
    if isinstance(sc, dict) and "error" not in sc and sc.get("found", 0) > 0:
        sc_lines = [f"Найдено записей: <b>{sc['found']}</b>\n"]
        for rec in sc.get("results", [])[:10]:
            row_parts = []
            if rec.get("username"):
                row_parts.append(f"👤 <code>{rec['username']}</code>")
            if rec.get("password"):
                row_parts.append(f"🔑 <code>{rec['password']}</code>")
            if rec.get("hash"):
                h = rec["hash"].lower()
                plain = cracked.get(h)
                if plain:
                    row_parts.append(f"🔓 <code>{plain}</code> <i>(взломан)</i>")
                else:
                    row_parts.append(f"🔒 <code>{h[:36]}</code>")
            if rec.get("ip"):
                row_parts.append(f"🖥 <code>{rec['ip']}</code>")
            if rec.get("source"):
                row_parts.append(f"<i>({rec['source']})</i>")
            if row_parts:
                sc_lines.append("  🔸 " + " | ".join(row_parts) + "\n")
        text += section("🔴 Scylla.sh (реальные данные)", sc_lines)

    # Cassandra.sh — реальные записи
    if isinstance(cas, dict) and "error" not in cas and cas.get("found", 0) > 0:
        cas_lines = [f"Найдено записей: <b>{cas['found']}</b>\n"]
        for rec in cas.get("results", [])[:8]:
            row_parts = []
            if rec.get("username"):
                row_parts.append(f"👤 <code>{rec['username']}</code>")
            if rec.get("password"):
                row_parts.append(f"🔑 <code>{rec['password']}</code>")
            if rec.get("hash"):
                h = rec["hash"].lower()
                plain = cracked.get(h)
                if plain:
                    row_parts.append(f"🔓 <code>{plain}</code> <i>(взломан)</i>")
                else:
                    row_parts.append(f"🔒 <code>{h[:36]}</code>")
            if rec.get("ip"):
                row_parts.append(f"🖥 <code>{rec['ip']}</code>")
            if rec.get("source"):
                row_parts.append(f"<i>({rec['source']})</i>")
            if row_parts:
                cas_lines.append("  🔸 " + " | ".join(row_parts) + "\n")
        text += section("🔴 Cassandra.sh (реальные данные)", cas_lines)

    # StopForumSpam
    if isinstance(sfs, dict) and "error" not in sfs and sfs.get("found"):
        freq = sfs.get("frequency", 0)
        conf = sfs.get("confidence", 0)
        last = sfs.get("lastseen", "")[:10]
        text += section("🚫 StopForumSpam", [
            f"<b>Email найден в базе спамеров!</b>\n"
            f"Встречался <b>{freq}</b> раз | Уверенность: {conf}% | Последний раз: {last}\n"
        ])

    # XposedOrNot — 400+ утечек + риск + категории данных
    if "error" not in xon and xon.get("found", 0) > 0:
        risk_emoji = {"Critical": "🔴", "High": "🟠", "Moderate": "🟡", "Low": "🟢"}.get(xon["risk_label"], "⚪")
        xon_lines = [
            f"{risk_emoji} Риск: <b>{xon['risk_label']}</b> ({xon['risk_score']}/100) | "
            f"Утечек: <b>{xon['found']}</b>\n"
        ]
        # Пароли
        pwd = xon.get("passwords", {})
        if pwd:
            plain = pwd.get("PlainText", 0)
            easy = pwd.get("EasyToCrack", 0)
            strong = pwd.get("StrongHash", 0)
            xon_lines.append(f"Пароли: открытых <b>{plain}</b> | слабых <b>{easy}</b> | хэшей <b>{strong}</b>\n")
        # Категории данных
        cats = xon.get("exposed_categories", [])
        if cats:
            cat_str = " · ".join(f"{c['name']} ({c['count']})" for c in cats[:6])
            xon_lines.append(f"Данные: <i>{cat_str}</i>\n")
        # Список утечек (первые 20)
        breaches = xon.get("breaches", [])
        if breaches:
            shown = breaches[:20]
            xon_lines.append("  " + " · ".join(shown) + "\n")
            if len(breaches) > 20:
                xon_lines.append(f"  <i>...и ещё {len(breaches) - 20}</i>\n")
        text += section("XposedOrNot (400+ баз)", xon_lines)

    # LeakCheck public (без ключа — список источников)
    if "error" not in lc_pub and lc_pub.get("found", 0) > 0:
        sources = lc_pub.get("sources", [])
        fields = lc_pub.get("fields", [])
        src_lines = [f"Найдено в <b>{lc_pub['found']:,}</b> записях из {len(sources)} источников\n"]
        if fields:
            src_lines.append(f"Утекло: <i>{', '.join(fields)}</i>\n")
        for s in sources[:15]:
            date = f" ({s['date']})" if s.get("date") else ""
            src_lines.append(f"  🔸 {s['name']}{date}\n")
        # Ссылки для ручной проверки
        encoded = email.replace("@", "%40")
        src_lines.append(
            f'\n🔗 <a href="https://leakcheck.io/check?q={encoded}">LeakCheck</a> · '
            f'<a href="https://dehashed.com/search?query={encoded}">DeHashed</a> · '
            f'<a href="https://haveibeenpwned.com/account/{encoded}">HIBP</a>\n'
        )
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

    parts = _split_msg(text)
    await msg.edit_text(parts[0], parse_mode="HTML", disable_web_page_preview=True)
    for part in parts[1:]:
        await message.answer(part, parse_mode="HTML", disable_web_page_preview=True)
