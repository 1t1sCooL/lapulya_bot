"""
Отдельные команды для каждого сервиса — для тестирования и точечного использования.
"""
import asyncio
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.wayback import wayback_availability, wayback_history
from modules.htmlweb_phone import htmlweb_phone, whatsapp_check
from modules.wmn_lookup import wmn_search
from modules.holehe_lookup import holehe_check
from modules.maigret_lookup import maigret_search, group_by_category
from modules.proxynova import proxynova_search
from modules.xposedornot import xon_check_email
from modules.intelx import intelx_search
from modules.email_lookup import hibp_check
from modules.hudsonrock import hudsonrock_email, hudsonrock_domain, hudsonrock_username
from modules.stopforumspam import sfs_check
from modules.tor_check import is_tor_exit
from modules.leakcheck import leakcheck_public
from modules.hashcrack import crack_hash, detect_hash_type
import config

router = Router()
log = logging.getLogger(__name__)


def _arg(text: str, cmd: str) -> str:
    """Извлекает аргумент из команды."""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


# ══════════════════════════════════════════════════════
#  ТЕЛЕФОН
# ══════════════════════════════════════════════════════

@router.message(Command("wa"))
async def cmd_wa(message: Message):
    """WhatsApp — проверка регистрации номера."""
    phone = _arg(message.text, "wa")
    if not phone:
        await message.answer("Использование: <code>/wa +79001234567</code>", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 Проверяю WhatsApp для <code>{phone}</code>...", parse_mode="HTML")
    r = await whatsapp_check(phone)
    wa = r.get("wa_link", "")
    reg = r.get("registered")
    if reg is True:
        status = "✅ Зарегистрирован"
    elif reg is False:
        status = "❌ Не найден"
    else:
        status = "❓ Не удалось определить — проверь вручную"
    text = (
        f"📱 <b>WhatsApp: {phone}</b>\n\n"
        f"{status}\n"
        f'🔗 <a href="{wa}">Открыть чат в WhatsApp</a>'
    )
    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("htmlweb"))
async def cmd_htmlweb(message: Message):
    """htmlweb.ru — оператор и регион номера без ключа."""
    phone = _arg(message.text, "htmlweb")
    if not phone:
        await message.answer("Использование: <code>/htmlweb +79001234567</code>", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 htmlweb.ru: <code>{phone}</code>...", parse_mode="HTML")
    r = await htmlweb_phone(phone)
    if "error" in r:
        await msg.edit_text(f"⚠️ {r['error']}", parse_mode="HTML")
        return
    text = (
        f"📱 <b>htmlweb.ru: {phone}</b>\n\n"
        f"🌍 Страна: {r.get('country','?')}\n"
        f"📍 Регион: {r.get('region','?')}\n"
        f"🏙 Город: {r.get('city','?')}\n"
        f"📡 Оператор: {r.get('operator','?')}\n"
        f"🕐 Таймзона: {r.get('timezone','?')}"
    )
    await msg.edit_text(text, parse_mode="HTML")


# ══════════════════════════════════════════════════════
#  EMAIL
# ══════════════════════════════════════════════════════

@router.message(Command("holehe"))
async def cmd_holehe(message: Message):
    """Holehe — на каких 144 сервисах зарегистрирован email."""
    email = _arg(message.text, "holehe")
    if not email:
        await message.answer("Использование: <code>/holehe user@example.com</code>", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 Holehe проверяет <code>{email}</code> на 144 сервисах...", parse_mode="HTML")
    r = await holehe_check(email)
    if "error" in r:
        await msg.edit_text(f"⚠️ Holehe: {r['error']}", parse_mode="HTML")
        return
    svcs = r.get("services", [])
    domains = r.get("domains", {})
    extras = r.get("extras", {})
    if not svcs:
        await msg.edit_text(
            f"🌐 <b>Holehe: {email}</b>\n\n❌ Не найден ни на одном из {r.get('checked',0)} сервисов.",
            parse_mode="HTML",
        )
        return
    icons = {"instagram":"📸","twitter":"🐦","discord":"🎮","spotify":"🎵","github":"💻",
             "google":"🔍","amazon":"📦","patreon":"💰","snapchat":"👻","tumblr":"✏️",
             "odnoklassniki":"🤝","mail_ru":"📧","rambler":"📧","adobe":"🎨","nike":"👟"}
    lines = [f"🌐 <b>Holehe: {email}</b>\n", f"Зарегистрирован на <b>{len(svcs)}</b> из {r.get('checked',0)} сервисов:\n"]
    for name in svcs:
        icon = icons.get(name, "🔹")
        domain = domains.get(name, name)
        extra = ""
        if name in extras:
            ex = extras[name]
            if ex.get("recovery_email"):
                extra = f" → резерв: <code>{ex['recovery_email']}</code>"
            elif ex.get("phone"):
                extra = f" → тел: <code>{ex['phone']}</code>"
        lines.append(f"  {icon} <b>{domain}</b>{extra}")
    await msg.edit_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("hibp"))
async def cmd_hibp(message: Message):
    """HIBP — Have I Been Pwned проверка email."""
    email = _arg(message.text, "hibp")
    if not email:
        await message.answer("Использование: <code>/hibp user@example.com</code>", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 HIBP: <code>{email}</code>...", parse_mode="HTML")
    r = await hibp_check(email)
    if "error" in r:
        await msg.edit_text(f"⚠️ HIBP: {r['error']}", parse_mode="HTML")
        return
    if not r.get("breached"):
        await msg.edit_text(f"✅ <b>HIBP: {email}</b>\n\nНе найден в известных утечках.", parse_mode="HTML")
        return
    lines = [f"🔴 <b>HIBP: {email}</b>\n\nНайден в <b>{r['count']}</b> утечках:\n"]
    for b in r.get("breaches", [])[:15]:
        classes = ", ".join(b.get("data_classes", [])[:3])
        lines.append(f"  🔸 <b>{b['name']}</b> ({b['date']}) — {classes}")
    await msg.edit_text("\n".join(lines), parse_mode="HTML")


@router.message(Command("xon"))
async def cmd_xon(message: Message):
    """XposedOrNot — 400+ баз утечек, риск-скор."""
    email = _arg(message.text, "xon")
    if not email:
        await message.answer("Использование: <code>/xon user@example.com</code>", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 XposedOrNot: <code>{email}</code>...", parse_mode="HTML")
    r = await xon_check_email(email)
    if "error" in r:
        await msg.edit_text(f"⚠️ XON: {r['error']}", parse_mode="HTML")
        return
    found = r.get("found", 0)
    if not found:
        await msg.edit_text(f"✅ <b>XposedOrNot: {email}</b>\n\nНе найден в 400+ базах.", parse_mode="HTML")
        return
    risk = r.get("risk_label", "?")
    score = r.get("risk_score", 0)
    emoji = {"Critical":"🔴","High":"🟠","Moderate":"🟡","Low":"🟢"}.get(risk,"⚪")
    breaches = r.get("breaches", [])
    cats = r.get("exposed_categories", [])
    lines = [
        f"🗄 <b>XposedOrNot: {email}</b>\n",
        f"{emoji} Риск: <b>{risk}</b> ({score}/100) | Утечек: <b>{found}</b>\n",
    ]
    if cats:
        lines.append("Утекло: " + " · ".join(f"{c['name']}({c['count']})" for c in cats[:6]) + "\n")
    if breaches:
        lines.append("Базы: " + " · ".join(breaches[:20]))
        if len(breaches) > 20:
            lines.append(f"\n<i>...и ещё {len(breaches)-20}</i>")
    await msg.edit_text("\n".join(lines), parse_mode="HTML")


@router.message(Command("proxynova"))
async def cmd_proxynova(message: Message):
    """Proxynova COMB — 3.2 млрд login:password пар."""
    query = _arg(message.text, "proxynova")
    if not query:
        await message.answer("Использование: <code>/proxynova user@example.com</code>", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 Proxynova: <code>{query}</code>...", parse_mode="HTML")
    r = await proxynova_search(query)
    if "error" in r:
        await msg.edit_text(f"⚠️ Proxynova: {r['error']}", parse_mode="HTML")
        return
    found = r.get("found", 0)
    if not found:
        await msg.edit_text(f"✅ <b>Proxynova: {query}</b>\n\nНе найден в COMB.", parse_mode="HTML")
        return
    lines = [f"🔴 <b>Proxynova COMB: {query}</b>\n\nНайдено записей: <b>{found:,}</b>\n"]
    for rec in r.get("results", [])[:15]:
        pwd = f" : <code>{rec['password']}</code>" if rec.get("password") else ""
        lines.append(f"  🔸 <code>{rec['login']}</code>{pwd}")
    await msg.edit_text("\n".join(lines), parse_mode="HTML")


@router.message(Command("intelx"))
async def cmd_intelx(message: Message):
    """IntelligenceX — поиск по пастам, дампам, даркнету."""
    query = _arg(message.text, "intelx")
    if not query:
        await message.answer("Использование: <code>/intelx query</code>", parse_mode="HTML")
        return
    if not config.INTELX_API_KEY:
        await message.answer("⚠️ INTELX_API_KEY не задан", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 IntelX: <code>{query}</code>...", parse_mode="HTML")
    r = await intelx_search(query, config.INTELX_API_KEY)
    if "error" in r:
        await msg.edit_text(f"⚠️ IntelX: {r['error']}", parse_mode="HTML")
        return
    found = r.get("found", 0)
    lines = [f"🗄 <b>IntelX: {query}</b>\n\nНайдено: <b>{found}</b> источников\n"]
    for rec in r.get("results", [])[:10]:
        lines.append(f"  📄 <b>{rec['name'][:60]}</b> <i>({rec.get('media','')}, {rec.get('date','')})</i>")
    await msg.edit_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("leakcheck"))
async def cmd_leakcheck(message: Message):
    """LeakCheck public — источники утечек для email."""
    email = _arg(message.text, "leakcheck")
    if not email:
        await message.answer("Использование: <code>/leakcheck user@example.com</code>", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 LeakCheck: <code>{email}</code>...", parse_mode="HTML")
    r = await leakcheck_public(email)
    if "error" in r:
        await msg.edit_text(f"⚠️ LeakCheck: {r['error']}", parse_mode="HTML")
        return
    found = r.get("found", 0)
    if not found:
        await msg.edit_text(f"✅ <b>LeakCheck: {email}</b>\n\nНе найден.", parse_mode="HTML")
        return
    sources = r.get("sources", [])
    fields = r.get("fields", [])
    lines = [f"🔴 <b>LeakCheck: {email}</b>\n\nЗаписей: <b>{found:,}</b> из {len(sources)} источников\n"]
    if fields:
        lines.append(f"Утекло: <i>{', '.join(fields)}</i>\n")
    for s in sources[:20]:
        date = f" ({s['date']})" if s.get("date") else ""
        lines.append(f"  🔸 {s['name']}{date}")
    await msg.edit_text("\n".join(lines), parse_mode="HTML")


# ══════════════════════════════════════════════════════
#  USERNAME
# ══════════════════════════════════════════════════════

@router.message(Command("wmn"))
async def cmd_wmn(message: Message):
    """WhatsMyName — 1500+ сайтов с позитивной верификацией."""
    username = _arg(message.text, "wmn").lstrip("@")
    if not username:
        await message.answer("Использование: <code>/wmn nickname</code>", parse_mode="HTML")
        return
    msg = await message.answer(
        f"🔍 WhatsMyName: <code>{username}</code> — загружаю базу 1500+ сайтов...",
        parse_mode="HTML",
    )
    r = await wmn_search(username)
    if "error" in r:
        await msg.edit_text(f"⚠️ WMN: {r['error']}", parse_mode="HTML")
        return
    found = r.get("found", 0)
    scanned = r.get("scanned", 0)
    if not found:
        await msg.edit_text(
            f"👤 <b>WMN: {username}</b>\n\n❌ Не найден ({scanned} сайтов проверено).",
            parse_mode="HTML",
        )
        return
    # Группируем по категориям
    cats: dict[str, list] = {}
    for rec in r.get("results", []):
        cat = rec.get("category", "Other") or "Other"
        cats.setdefault(cat, []).append(rec)

    lines = [f"👤 <b>WMN: {username}</b>\n\nНайден на <b>{found}</b> из {scanned} сайтов:\n"]
    for cat, items in sorted(cats.items()):
        lines.append(f"\n<b>{cat}</b>")
        for rec in items:
            lines.append(f"  🟢 <a href='{rec['url']}'>{rec['site']}</a>")

    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3880] + "\n<i>...обрезано</i>"
    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("maigret"))
async def cmd_maigret(message: Message):
    """Maigret — 3000+ сайтов."""
    username = _arg(message.text, "maigret").lstrip("@")
    if not username:
        await message.answer("Использование: <code>/maigret nickname</code>", parse_mode="HTML")
        return
    msg = await message.answer(
        f"🔍 Maigret: <code>{username}</code> — 3000+ сайтов (до 90 сек)...",
        parse_mode="HTML",
    )
    r = await maigret_search(username)
    if "error" in r and r.get("found", 0) == 0:
        await msg.edit_text(f"⚠️ Maigret: {r.get('error','')}", parse_mode="HTML")
        return
    found = r.get("found", 0)
    if not found:
        await msg.edit_text(f"👤 <b>Maigret: {username}</b>\n\n❌ Не найден.", parse_mode="HTML")
        return
    cats = group_by_category(r.get("results", []))
    lines = [f"👤 <b>Maigret: {username}</b>\n\nНайден на <b>{found}</b> сайтах:\n"]
    for cat, items in cats.items():
        lines.append(f"\n<b>{cat or 'Другое'}</b>")
        for rec in items[:20]:
            url = rec.get("url", "")
            if url:
                lines.append(f"  🟢 <a href='{url}'>{rec['site']}</a>")
            else:
                lines.append(f"  🟢 {rec['site']}")
    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3880] + "\n<i>...обрезано</i>"
    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


# ══════════════════════════════════════════════════════
#  ДОМЕН / IP
# ══════════════════════════════════════════════════════

@router.message(Command("wayback"))
async def cmd_wayback(message: Message):
    """Wayback Machine — история сайта."""
    url = _arg(message.text, "wayback")
    if not url:
        await message.answer("Использование: <code>/wayback example.com</code>", parse_mode="HTML")
        return
    if not url.startswith("http"):
        url = "https://" + url
    msg = await message.answer(f"🔍 Wayback Machine: <code>{url}</code>...", parse_mode="HTML")
    avail, history = await asyncio.gather(
        wayback_availability(url),
        wayback_history(url, limit=8),
    )
    lines = [f"🕰 <b>Wayback Machine: {url}</b>\n"]

    if "error" not in avail and avail.get("found"):
        ts = avail.get("timestamp", "")
        date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ts
        lines.append(f"📸 Последний снапшот: <b>{date}</b>")
        lines.append(f'🔗 <a href="{avail["snapshot"]}">Открыть</a>\n')
    else:
        lines.append("❌ Снапшотов не найдено\n")

    if "error" not in history and history.get("snapshots"):
        lines.append(f"\n<b>История ({len(history['snapshots'])} снапшотов):</b>")
        for s in history["snapshots"]:
            lines.append(f'  📅 <a href="{s["archive"]}">{s["date"]}</a>')

    await msg.edit_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


# ══════════════════════════════════════════════════════
#  РАЗНОЕ
# ══════════════════════════════════════════════════════

@router.message(Command("sfs"))
async def cmd_sfs(message: Message):
    """StopForumSpam — база спамеров/мошенников."""
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer(
            "Использование:\n"
            "<code>/sfs email user@example.com</code>\n"
            "<code>/sfs ip 1.2.3.4</code>\n"
            "<code>/sfs username johndoe</code>",
            parse_mode="HTML",
        )
        return
    qtype = parts[1].lower() if len(parts) > 1 else "email"
    query = parts[2].strip() if len(parts) > 2 else ""
    if not query:
        await message.answer("Укажи запрос после типа.", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 StopForumSpam: <code>{query}</code>...", parse_mode="HTML")
    r = await sfs_check(query, qtype)
    if "error" in r:
        await msg.edit_text(f"⚠️ SFS: {r['error']}", parse_mode="HTML")
        return
    if r.get("found"):
        freq = r.get("frequency", 0)
        conf = r.get("confidence", 0)
        last = r.get("lastseen", "")[:10]
        text = (
            f"🚫 <b>StopForumSpam: {query}</b>\n\n"
            f"Найден в базе спамеров!\n"
            f"Встречался: <b>{freq}</b> раз\n"
            f"Уверенность: {conf}%\n"
            f"Последний раз: {last}"
        )
    else:
        text = f"✅ <b>StopForumSpam: {query}</b>\n\nНе найден в базе спамеров."
    await msg.edit_text(text, parse_mode="HTML")


@router.message(Command("torcheck"))
async def cmd_torcheck(message: Message):
    """Tor check — проверка IP на Tor exit node."""
    ip = _arg(message.text, "torcheck")
    if not ip:
        await message.answer("Использование: <code>/torcheck 1.2.3.4</code>", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 Tor check: <code>{ip}</code>...", parse_mode="HTML")
    r = await is_tor_exit(ip)
    if r.get("is_tor"):
        text = f"🧅 <b>Tor: {ip}</b>\n\n⚠️ Это Tor exit node! (источник: {r.get('source','')})"
    else:
        text = f"✅ <b>Tor: {ip}</b>\n\nНе является Tor exit node."
    await msg.edit_text(text, parse_mode="HTML")


@router.message(Command("hudsonrock"))
async def cmd_hudsonrock(message: Message):
    """Hudson Rock — инфостилеры по email/username/domain."""
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Использование:\n"
            "<code>/hudsonrock email user@example.com</code>\n"
            "<code>/hudsonrock username johndoe</code>\n"
            "<code>/hudsonrock domain example.com</code>",
            parse_mode="HTML",
        )
        return
    qtype, query = parts[1].lower(), parts[2].strip()
    msg = await message.answer(f"🔍 Hudson Rock: <code>{query}</code>...", parse_mode="HTML")
    if qtype == "email":
        r = await hudsonrock_email(query)
    elif qtype == "username":
        r = await hudsonrock_username(query)
    elif qtype == "domain":
        r = await hudsonrock_domain(query)
    else:
        await msg.edit_text("Тип: email / username / domain", parse_mode="HTML")
        return
    if "error" in r:
        await msg.edit_text(f"⚠️ HudsonRock: {r['error']}", parse_mode="HTML")
        return
    found = r.get("found", 0)
    if not found:
        await msg.edit_text(f"✅ <b>HudsonRock: {query}</b>\n\nНе найден.", parse_mode="HTML")
        return
    lines = [f"🚨 <b>HudsonRock: {query}</b>\n\nЗаражённых машин: <b>{found}</b>\n"]
    for s in r.get("stealers", [])[:5]:
        lines.append(f"  🦠 {s['date']} | {s['computer'] or '?'} | {s['total_services']} сервисов")
    await msg.edit_text("\n".join(lines), parse_mode="HTML")


@router.message(Command("crack"))
async def cmd_crack(message: Message):
    """Взлом хэша через rainbow tables (MD5/SHA1/SHA256)."""
    h = _arg(message.text, "crack").strip().lower()
    if not h:
        await message.answer("Использование: <code>/crack 5d41402abc4b2a76b9719d911017c592</code>", parse_mode="HTML")
        return
    htype = detect_hash_type(h)
    if not htype:
        await message.answer(f"⚠️ <code>{h}</code> — не похоже на MD5/SHA1/SHA256", parse_mode="HTML")
        return
    msg = await message.answer(f"🔍 Взламываю {htype}: <code>{h}</code>...", parse_mode="HTML")
    result = await crack_hash(h)
    if result:
        await msg.edit_text(
            f"🔓 <b>Взломан!</b>\n\n"
            f"Хэш: <code>{h}</code>\n"
            f"Тип: {htype}\n"
            f"Пароль: <code>{result}</code>",
            parse_mode="HTML",
        )
    else:
        await msg.edit_text(
            f"❌ <b>Не удалось взломать</b>\n\n"
            f"Хэш: <code>{h}</code> ({htype})\n"
            f"<i>Хэш не найден в rainbow tables</i>",
            parse_mode="HTML",
        )
