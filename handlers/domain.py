import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.domain_lookup import whois_lookup, dns_lookup, get_ip_geolocation, get_ssl_info
from utils.formatter import kv, section, list_items, error_msg

router = Router()


@router.message(Command("domain"))
async def cmd_domain(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: <code>/domain example.com</code>", parse_mode="HTML")
        return
    domain = args[1].strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
    msg = await message.answer(f"🔍 Анализирую <code>{domain}</code>...", parse_mode="HTML")

    whois, dns, ssl = await asyncio.gather(
        whois_lookup(domain),
        dns_lookup(domain),
        get_ssl_info(domain),
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

    geo = await get_ip_geolocation(ip)

    if "error" in geo:
        await msg.edit_text(error_msg(geo["error"]), parse_mode="HTML")
        return

    lines = [
        kv("IP", geo.get("ip")),
        kv("Город", geo.get("city")),
        kv("Регион", geo.get("region")),
        kv("Страна", geo.get("country")),
        kv("Организация", geo.get("org")),
        kv("ASN", geo.get("asn")),
        kv("Часовой пояс", geo.get("timezone")),
        kv("Координаты", f"{geo.get('latitude')}, {geo.get('longitude')}"),
    ]

    text = f"🖥 <b>OSINT: IP {ip}</b>\n"
    text += section("Геолокация", lines)
    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
