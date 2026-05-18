import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.leakcheck import leakcheck_search
from modules.intelx import intelx_search, intelx_phonebook, intelx_file_preview
from modules.dehashed import dehashed_search
from modules.breachdirectory import breachdirectory_search
from modules.email_lookup import hibp_check
from modules.proxynova import proxynova_search
from modules.hudsonrock import hudsonrock_email, hudsonrock_username, hudsonrock_domain
from modules.xposedornot import xon_check_email, pwned_password
from modules.scylla import scylla_search
from modules.cassandra import cassandra_search
from modules.stopforumspam import sfs_check
from modules.hashcrack import crack_hashes_batch, detect_hash_type
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
    "  <code>/breach ip 1.2.3.4</code>\n"
    "  <code>/breach password mypassword</code>\n\n"
    "Источники: Scylla · XposedOrNot · LeakCheck · Dehashed · IntelX · HIBP · HudsonRock · Proxynova"
)


@router.message(Command("breach"))
async def cmd_breach(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    query_type = parts[1].lower()
    query = parts[2].strip()

    valid_types = {"email", "phone", "username", "domain", "name", "ip", "password"}
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

    # Специальный обработчик для пароля
    if query_type == "password":
        count = await pwned_password(query)
        if count < 0:
            await msg.edit_text("⚠️ Не удалось проверить пароль", parse_mode="HTML")
        elif count == 0:
            await msg.edit_text(
                f"🔑 <b>Пароль:</b> <code>{'*' * len(query)}</code>\n\n"
                "✅ <b>Не найден</b> в базах утечек HIBP.\n"
                "<i>Это не гарантирует безопасность — могут быть другие базы.</i>",
                parse_mode="HTML"
            )
        else:
            await msg.edit_text(
                f"🔑 <b>Пароль:</b> <code>{'*' * len(query)}</code>\n\n"
                f"🔴 <b>Найден {count:,} раз</b> в базах утечек!\n"
                "<b>Немедленно смени этот пароль везде где используется.</b>\n\n"
                "<i>⚠️ Пароль проверяется через k-anonymity — полный пароль никуда не отправляется.</i>",
                parse_mode="HTML"
            )
        return

    # Запускаем все источники параллельно
    tasks = _build_tasks(query_type, query)
    results_raw = await asyncio.gather(*tasks.values(), return_exceptions=True)
    results = dict(zip(tasks.keys(), results_raw))

    # Превью IntelX файлов для топ-3 результатов
    ix_previews = {}
    if config.INTELX_API_KEY:
        ix = results.get("intelx", {})
        if isinstance(ix, dict) and ix.get("results"):
            preview_tasks = {}
            for rec in ix["results"][:3]:
                sid = rec.get("storageid")
                if sid:
                    preview_tasks[sid] = intelx_file_preview(sid, config.INTELX_API_KEY, lines=8)
            if preview_tasks:
                previews_raw = await asyncio.gather(*preview_tasks.values())
                ix_previews = dict(zip(preview_tasks.keys(), previews_raw))

    # Собираем все хэши из всех источников и взламываем параллельно
    all_hashes = _collect_hashes(results)
    cracked = {}
    if all_hashes:
        cracked = await crack_hashes_batch(list(all_hashes))

    text = _format_results(query, query_type, results, ix_previews, cracked)
    parts = _split_message(text)
    await msg.edit_text(parts[0], parse_mode="HTML", disable_web_page_preview=True)
    for part in parts[1:]:
        await message.answer(part, parse_mode="HTML", disable_web_page_preview=True)


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

    # XposedOrNot — 400+ баз, бесплатно
    if query_type == "email":
        tasks["xon"] = xon_check_email(query)

    # Scylla.sh / Cassandra.sh — временно отключены (домены недоступны)

    # StopForumSpam — база спамеров/мошенников, бесплатно
    if query_type in ("email", "ip", "username"):
        sfs_type = query_type if query_type in ("email", "ip", "username") else "email"
        tasks["sfs"] = sfs_check(query, sfs_type)

    return tasks


def _split_message(text: str, limit: int = 3900) -> list[str]:
    """Разбивает длинное сообщение на части по 3900 символов, не ломая теги."""
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


def _collect_hashes(results: dict) -> set:
    """Собирает все хэши из всех источников для авто-взлома."""
    hashes = set()
    for key in ("leakcheck", "dehashed", "scylla"):
        src = results.get(key)
        if not isinstance(src, dict):
            continue
        for rec in src.get("results", []):
            h = rec.get("hash") or rec.get("password_hash", "")
            if h and detect_hash_type(h):
                hashes.add(h.strip().lower())
    return hashes


def _format_results(query: str, query_type: str, results: dict, ix_previews: dict = None, cracked: dict = None) -> str:
    lines = [f"🗄 <b>Пробив: <code>{query}</code></b> [{query_type}]\n"]
    any_found = False

    cracked = cracked or {}

    # ── Scylla.sh ────────────────────────────────────────────────────
    sc = results.get("scylla")
    if isinstance(sc, dict) and "error" not in sc:
        count = sc.get("found", 0)
        any_found = any_found or count > 0
        if count > 0:
            lines.append(f"\n<b>🔴 Scylla.sh</b> — найдено записей: <b>{count}</b>")
            for rec in sc.get("results", [])[:12]:
                row = _fmt_scylla_record(rec, cracked)
                if row:
                    lines.append(row)
        else:
            lines.append("\n<b>Scylla.sh:</b> ✅ не найдено")
    elif isinstance(sc, dict):
        lines.append(f"\n<b>Scylla.sh:</b> ⚠️ {sc['error']}")

    # ── Cassandra.sh ─────────────────────────────────────────────────
    cas = results.get("cassandra")
    if isinstance(cas, dict) and "error" not in cas and cas.get("found", 0) > 0:
        any_found = True
        lines.append(f"\n<b>🔴 Cassandra.sh</b> — найдено записей: <b>{cas['found']}</b>")
        for rec in cas.get("results", [])[:10]:
            row = _fmt_scylla_record(rec, cracked)
            if row:
                lines.append(row)

    # ── StopForumSpam ─────────────────────────────────────────────────
    sfs = results.get("sfs")
    if isinstance(sfs, dict) and "error" not in sfs and sfs.get("found"):
        any_found = True
        conf = sfs.get("confidence", 0)
        freq = sfs.get("frequency", 0)
        last = sfs.get("lastseen", "")[:10]
        lines.append(
            f"\n<b>🚫 StopForumSpam</b> — <b>найден в базе спамеров!</b>\n"
            f"  Встречался <b>{freq}</b> раз | Уверенность: {conf}% | Последний раз: {last}"
        )

    # ── LeakCheck ────────────────────────────────────────────────────
    lc = results.get("leakcheck")
    if isinstance(lc, dict) and "error" not in lc:
        count = lc.get("found", 0)
        any_found = any_found or count > 0
        lines.append(f"\n<b>🔴 LeakCheck</b> — найдено записей: <b>{count}</b>")
        for rec in lc.get("results", [])[:10]:
            row = _fmt_leak_record(rec, cracked)
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
            row = _fmt_dehashed_record(rec, cracked)
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
                    f"\n  📄 <b>{rec['name'][:60]}</b> "
                    f"<i>({rec.get('media', '')}, {rec.get('date', '')})</i>"
                )
                sid = rec.get("storageid", "")
                if ix_previews and sid in ix_previews:
                    preview = ix_previews[sid]
                    if preview and not preview.startswith("⚠️"):
                        # Показываем превью в блоке кода
                        preview_lines = preview.split("\n")[:6]
                        escaped = "\n".join(preview_lines)
                        lines.append(f"<pre>{escaped[:600]}</pre>")
                    else:
                        lines.append(f"  <i>{preview}</i>")
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

    # ── XposedOrNot ──────────────────────────────────────────────────
    xon = results.get("xon")
    if isinstance(xon, dict) and "error" not in xon and xon.get("found", 0) > 0:
        any_found = True
        risk_emoji = {"Critical": "🔴", "High": "🟠", "Moderate": "🟡", "Low": "🟢"}.get(xon.get("risk_label", ""), "⚪")
        lines.append(f"\n<b>{risk_emoji} XposedOrNot</b> — {xon['found']} утечек | риск: <b>{xon.get('risk_label','?')}</b> ({xon.get('risk_score',0)}/100)")
        breaches = xon.get("breaches", [])[:15]
        if breaches:
            lines.append("  " + " · ".join(breaches))
        if len(xon.get("breaches", [])) > 15:
            lines.append(f"  <i>...и ещё {len(xon['breaches']) - 15}</i>")
    elif isinstance(xon, dict) and "error" in xon:
        lines.append(f"\n<b>XposedOrNot:</b> ⚠️ {xon['error']}")

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

    return "\n".join(lines)


def _fmt_scylla_record(rec: dict, cracked: dict) -> str:
    parts = []
    if rec.get("email"):
        parts.append(f"📧 <code>{rec['email']}</code>")
    if rec.get("username"):
        parts.append(f"👤 <code>{rec['username']}</code>")
    if rec.get("name"):
        parts.append(f"🧑 {rec['name']}")
    if rec.get("password"):
        parts.append(f"🔑 <code>{rec['password']}</code>")
    if rec.get("hash"):
        h = rec["hash"].lower()
        plain = cracked.get(h)
        if plain:
            parts.append(f"🔓 <code>{plain}</code> <i>(взломан)</i>")
        else:
            parts.append(f"🔒 <code>{h[:40]}</code>")
    if rec.get("ip"):
        parts.append(f"🖥 <code>{rec['ip']}</code>")
    if rec.get("phone"):
        parts.append(f"📱 <code>{rec['phone']}</code>")
    if rec.get("source"):
        parts.append(f"<i>({rec['source']})</i>")
    return "  🔸 " + " | ".join(parts) if parts else ""


def _fmt_leak_record(rec: dict, cracked: dict = None) -> str:
    cracked = cracked or {}
    parts = []
    if rec.get("email"):
        parts.append(f"📧 <code>{rec['email']}</code>")
    if rec.get("username"):
        parts.append(f"👤 <code>{rec['username']}</code>")
    if rec.get("password"):
        parts.append(f"🔑 <code>{rec['password']}</code>")
    elif rec.get("password_hash"):
        h = rec["password_hash"].lower()
        plain = cracked.get(h)
        if plain:
            parts.append(f"🔓 <code>{plain}</code> <i>(взломан)</i>")
        else:
            parts.append(f"🔒 <code>{h[:40]}</code>")
    if rec.get("phone"):
        parts.append(f"📱 <code>{rec['phone']}</code>")
    if rec.get("source"):
        parts.append(f"<i>({rec['source']})</i>")
    return "  🔸 " + " | ".join(parts) if parts else ""


def _fmt_dehashed_record(rec: dict, cracked: dict = None) -> str:
    cracked = cracked or {}
    parts = []
    if rec.get("email"):
        parts.append(f"📧 <code>{rec['email']}</code>")
    if rec.get("username"):
        parts.append(f"👤 <code>{rec['username']}</code>")
    if rec.get("password"):
        parts.append(f"🔑 <code>{rec['password']}</code>")
    elif rec.get("hashed_password"):
        h = rec["hashed_password"].lower()
        plain = cracked.get(h)
        if plain:
            parts.append(f"🔓 <code>{plain}</code> <i>(взломан)</i>")
        else:
            parts.append(f"🔒 <code>{h[:40]}</code>")
    if rec.get("name"):
        parts.append(f"🧑 <code>{rec['name']}</code>")
    if rec.get("phone"):
        parts.append(f"📱 <code>{rec['phone']}</code>")
    if rec.get("ip"):
        parts.append(f"🖥 <code>{rec['ip']}</code>")
    if rec.get("database"):
        parts.append(f"<i>({rec['database']})</i>")
    return "  🔸 " + " | ".join(parts) if parts else ""
