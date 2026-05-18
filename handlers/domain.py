import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.domain_lookup import whois_lookup, dns_lookup, get_ip_geolocation, get_ssl_info, internetdb_lookup
from modules.greynoise import greynoise_ip
from modules.abuseipdb import abuseipdb_check
from modules.hunter import hunter_domain_search
from modules.ipqualityscore import ipqs_ip
from utils.formatter import kv, section, list_items, error_msg
import config

router = Router()


@router.message(Command("domain"))
async def cmd_domain(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: <code>/domain example.com</code>", parse_mode="HTML")
        return
    domain = args[1].strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
    msg = await message.answer(f"🔍 Анализирую <code>{domain}</code>...", parse_mode="HTML")

    whois, dns, ssl, hunter = await asyncio.gather(
        whois_lookup(domain),
        dns_lookup(domain),
        get_ssl_info(domain),
        hunter_domain_search(domain, config.HUNTER_API_KEY) if config.HUNTER_API_KEY else asyncio.sleep(0, result={}),
    )

    # WHOIS
    w_lines = [
        kv("Регистратор", whois.get("registrar")),
        kv("Создан", whois.get("creation_date")),
        kv("Истекает", whois.get("expiration_date")),
        kv("Обновлён", whois.get("updated_date")),
        kv("Организация", whois.get("org")),
        kv("Страна", whois.get("country")),
        kv("Email", ", ".join(whois.get("emails", [])[:3])),
    ]
    if whois.get("name_servers"):
        w_lines.append(f"<b>NS:</b>\n{list_items(whois['name_servers'][:5])}")

    # DNS
    d_lines = []
    for rtype, records in dns.items():
        d_lines.append(f"<b>{rtype}:</b>\n{list_items(records)}")

    # Subdomains via crt.sh
    s_lines = []
    if ssl.get("subdomains"):
        s_lines.append(f"Найдено через crt.sh ({ssl.get('total_certs', 0)} сертификатов):\n")
        s_lines.append(list_items(ssl["subdomains"]))

    text = f"🌐 <b>OSINT: {domain}</b>\n"
    text += section("WHOIS", w_lines)
    text += section("DNS", d_lines)
    text += section("Субдомены (crt.sh)", s_lines)

    # Hunter.io — email-адреса на домене
    if isinstance(hunter, dict) and "error" not in hunter and hunter.get("found", 0) > 0:
        h_lines = [f"Найдено {hunter['found']} из {hunter.get('total', '?')} | Организация: {hunter.get('organization', '?')}\n"]
        for e in hunter.get("emails", [])[:15]:
            pos = f" — {e['position']}" if e.get("position") else ""
            conf = f" ({e['confidence']}%)" if e.get("confidence") else ""
            name = f"{e.get('first_name', '')} {e.get('last_name', '')}".strip()
            h_lines.append(f"  📧 <code>{e['email']}</code>{conf}{' · ' + name if name else ''}{pos}\n")
        text += section("Hunter.io (email на домене)", h_lines)

    if not (w_lines or d_lines or s_lines):
        text = error_msg(f"Нет данных для {domain}")

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("ip"))
async def cmd_ip(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: <code>/ip 8.8.8.8</code>", parse_mode="HTML")
        return
    ip = args[1].strip()
    msg = await message.answer(f"🔍 Анализирую IP <code>{ip}</code>...", parse_mode="HTML")

    geo, idb, gn, abuse, ipqs = await asyncio.gather(
        get_ip_geolocation(ip),
        internetdb_lookup(ip),
        greynoise_ip(ip, config.GREYNOISE_API_KEY) if config.GREYNOISE_API_KEY else asyncio.sleep(0, result={}),
        abuseipdb_check(ip, config.ABUSEIPDB_API_KEY) if config.ABUSEIPDB_API_KEY else asyncio.sleep(0, result={}),
        ipqs_ip(ip, config.IPQS_API_KEY) if config.IPQS_API_KEY else asyncio.sleep(0, result={}),
    )

    if "error" in geo:
        await msg.edit_text(error_msg(geo["error"]), parse_mode="HTML")
        return

    text = f"🖥 <b>OSINT: IP {ip}</b>\n"

    geo_lines = [
        kv("Город", geo.get("city")),
        kv("Регион", geo.get("region")),
        kv("Страна", geo.get("country")),
        kv("Организация", geo.get("org")),
        kv("ASN", geo.get("asn")),
        kv("Часовой пояс", geo.get("timezone")),
        kv("Координаты", f"{geo.get('latitude')}, {geo.get('longitude')}"),
    ]
    text += section("Геолокация", geo_lines)

    if "error" not in idb:
        idb_lines = []
        if idb.get("hostnames"):
            idb_lines.append(kv("Хостнеймы", ", ".join(idb["hostnames"][:5])))
        if idb.get("ports"):
            ports_str = ", ".join(str(p) for p in sorted(idb["ports"]))
            idb_lines.append(kv("Открытые порты", ports_str))
        if idb.get("tags"):
            idb_lines.append(kv("Теги", ", ".join(idb["tags"])))
        if idb.get("cpes"):
            idb_lines.append("<b>CPE:</b>\n" + "".join(f"  • <code>{c}</code>\n" for c in idb["cpes"][:5]))
        if idb.get("vulns"):
            vulns = idb["vulns"][:10]
            idb_lines.append(f"<b>⚠️ CVE ({len(idb['vulns'])} шт.):</b>\n" + "".join(f"  • <code>{v}</code>\n" for v in vulns))
        if idb_lines:
            text += section("Shodan InternetDB", idb_lines)

    # GreyNoise
    if isinstance(gn, dict) and "error" not in gn and gn.get("found"):
        cl = gn.get("classification", "")
        emoji = {"malicious": "🔴", "benign": "🟢", "unknown": "⚪"}.get(cl, "⚪")
        gn_lines = [
            kv("Статус", f"{emoji} {cl}"),
            kv("Шум", "Да (активно сканирует интернет)" if gn.get("noise") else "Нет"),
            kv("RIOT", "Да (известный сервис)" if gn.get("riot") else "Нет"),
            kv("Имя", gn.get("name")),
            kv("Последний раз", gn.get("last_seen")),
        ]
        text += section("GreyNoise", gn_lines)

    # AbuseIPDB
    if isinstance(abuse, dict) and "error" not in abuse and abuse.get("total_reports", 0) > 0:
        score = abuse.get("abuse_score", 0)
        score_emoji = "🔴" if score >= 50 else ("🟠" if score >= 20 else "🟡")
        ab_lines = [
            kv("Оценка угрозы", f"{score_emoji} {score}/100"),
            kv("Жалоб", str(abuse.get("total_reports", 0))),
            kv("Страна", abuse.get("country")),
            kv("ISP", abuse.get("isp")),
            kv("Использование", abuse.get("usage_type")),
            kv("TOR", "Да" if abuse.get("is_tor") else "Нет"),
            kv("Последняя жалоба", abuse.get("last_reported", "")[:10]),
        ]
        if abuse.get("categories"):
            ab_lines.append(kv("Типы атак", " · ".join(abuse["categories"][:6])))
        text += section("AbuseIPDB", ab_lines)

    # IPQualityScore
    if isinstance(ipqs, dict) and "error" not in ipqs and ipqs:
        fs = ipqs.get("fraud_score", 0)
        fs_emoji = "🔴" if fs >= 75 else ("🟠" if fs >= 40 else "🟢")
        flags = []
        if ipqs.get("proxy"):   flags.append("Прокси")
        if ipqs.get("vpn"):     flags.append("VPN")
        if ipqs.get("tor"):     flags.append("Tor")
        if ipqs.get("bot_status"): flags.append("Бот")
        if ipqs.get("recent_abuse"): flags.append("Недавние злоупотребления")
        ipqs_lines = [
            kv("Фрод-скор", f"{fs_emoji} {fs}/100"),
            kv("Тип подключения", ipqs.get("connection_type")),
            kv("Флаги", " · ".join(flags) if flags else "нет"),
            kv("ISP", ipqs.get("isp")),
            kv("Организация", ipqs.get("organization")),
        ]
        text += section("IPQualityScore", ipqs_lines)

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
