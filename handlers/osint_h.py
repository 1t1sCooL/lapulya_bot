import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.osint_aggregator import detect_query_type, osint_search
from utils.formatter import section, kv, error_msg
import config

router = Router()
log = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>/osint</b> — Сводный OSINT-отчёт\n\n"
    "Автоматически определяет тип запроса и запускает все подходящие источники.\n\n"
    "Примеры:\n"
    "  <code>/osint +79001234567</code> — номер телефона\n"
    "  <code>/osint user@example.com</code> — email\n"
    "  <code>/osint 7707083893</code> — ИНН (10 цифр — юрлицо)\n"
    "  <code>/osint example.com</code> — домен / URL\n"
    "  <code>/osint 8.8.8.8</code> — IP-адрес\n"
    "  <code>/osint durov</code> — @username (все соцсети)\n"
    "  <code>/osint Иванов Иван</code> — ФИО\n"
    "  <code>/osint А123БВ77</code> — госномер\n"
    "  <code>/osint 4510 123456</code> — паспорт\n"
    "  <code>/osint 77:01:0001001:1</code> — кадастровый номер"
)

_TYPE_LABELS = {
    "phone": "📱 номер телефона",
    "email": "📧 email-адрес",
    "inn_ul": "🏢 ИНН юрлица (10 цифр)",
    "inn_fl": "👤 ИНН физлица (12 цифр)",
    "domain": "🌐 домен / URL",
    "ip": "🖥 IP-адрес",
    "username": "👤 username / никнейм",
    "fio": "📋 ФИО",
    "car": "🚗 госномер",
    "passport": "📄 серия+номер паспорта",
    "cadastral": "🏠 кадастровый номер",
}


@router.message(Command("osint"))
async def cmd_osint(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    query = args[1].strip()
    qtype = detect_query_type(query)
    type_label = _TYPE_LABELS.get(qtype, qtype)

    log.debug(
        "cmd_osint: запрос %r → тип=%s от user_id=%s",
        query, qtype, message.from_user.id if message.from_user else "?",
    )

    msg = await message.answer(
        f"🔍 Определил как: <b>{type_label}</b>\n"
        f"Запрос: <code>{query}</code>\n\n"
        f"⏳ Собираю данные из всех источников...",
        parse_mode="HTML",
    )

    result = await osint_search(
        query,
        leakcheck_key=config.LEAKCHECK_API_KEY,
        dehashed_email=config.DEHASHED_EMAIL,
        dehashed_key=config.DEHASHED_API_KEY,
        intelx_key=config.INTELX_API_KEY,
        getcontact_token=config.GETCONTACT_TOKEN,
    )

    sources = result.get("results", {})
    text = f"🕵️ <b>OSINT: {query}</b>\n"
    text += f"<i>Тип: {type_label}</i>\n"

    if not sources:
        text += "\n🔍 Ничего не найдено."
        await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
        return

    any_result = False

    for source_key, data in sources.items():
        block = _fmt_source(source_key, data, qtype)
        if block:
            text += block
            any_result = True

    if not any_result:
        text += "\n🔍 Ничего не найдено."

    if len(text) > 4000:
        text = text[:3980] + "\n\n<i>… обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


def _fmt_source(source_key: str, data: dict, qtype: str) -> str:
    """Форматирует один источник для отчёта."""
    if not isinstance(data, dict):
        return ""

    if "error" in data:
        err = data["error"]
        # Не показывать ошибки "ключ не задан" — только реальные проблемы
        if "не задан" in err or "not set" in err.lower():
            return ""
        return section(source_key.upper(), [f"⚠️ {err}\n"])

    labels = {
        "phone_info": "Номер телефона",
        "leakcheck": "LeakCheck",
        "getcontact": "GetContact",
        "vk": "VK",
        "tg": "Telegram",
        "ok": "OK.ru",
        "instagram": "Instagram",
        "twitter": "Twitter/X",
        "hibp": "HIBP",
        "egrul": "ЕГРЮЛ",
        "whois": "WHOIS",
        "dns": "DNS",
        "geo": "Геолокация IP",
        "fio": "Поиск по ФИО",
        "car": "ГИБДД",
        "passport": "Паспорт МВД",
        "rosreestr": "Росреестр",
    }
    title = labels.get(source_key, source_key.upper())

    # ── телефон ──
    if source_key == "phone_info":
        lines = [
            kv("Формат", data.get("international")),
            kv("Регион", data.get("region")),
            kv("Оператор", data.get("carrier")),
            kv("Тип", data.get("number_type")),
            kv("Валидный", "✅ Да" if data.get("valid") else "❌ Нет"),
        ]
        return section(title, lines)

    # ── LeakCheck ──
    if source_key == "leakcheck":
        found = data.get("found", 0)
        if not found:
            return ""
        lines = [f"Найдено: <b>{found}</b> записей\n"]
        for rec in data.get("results", [])[:5]:
            parts = []
            if rec.get("email"):
                parts.append(f"📧 <code>{rec['email']}</code>")
            if rec.get("username"):
                parts.append(f"👤 <code>{rec['username']}</code>")
            if rec.get("source"):
                parts.append(f"<i>({rec['source']})</i>")
            if parts:
                lines.append("  🔸 " + " | ".join(parts) + "\n")
        return section(title, lines)

    # ── GetContact ──
    if source_key == "getcontact":
        names = data.get("names") or data.get("tags") or []
        if not names:
            return ""
        lines = [f"Теги: {', '.join(str(n) for n in names[:10])}\n"]
        return section(title, lines)

    # ── VK ──
    if source_key == "vk":
        items = data.get("results") if isinstance(data.get("results"), list) else None
        if items:
            lines = [f"Профилей: <b>{data.get('found', len(items))}</b>\n"]
            for u in items[:5]:
                lock = "🔒" if u.get("is_closed") else "🔓"
                lines.append(f"  {lock} <a href='{u.get('url', '')}'>{u.get('name', '?')}</a>\n")
            return section(title, lines)
        # прямой профиль
        if data.get("name"):
            url = f"https://vk.com/{data.get('screen_name', '')}"
            lines = [
                kv("Имя", data.get("name")),
                kv("Профиль", f'<a href="{url}">{data.get("screen_name", "")}</a>'),
                kv("Город", data.get("city")),
                kv("Подписчики", data.get("followers")),
            ]
            return section(title, lines)
        return ""

    # ── Telegram ──
    if source_key == "tg":
        if not data.get("name") and not data.get("username"):
            return ""
        lines = [
            kv("Username", data.get("username")),
            kv("Имя", data.get("name")),
            kv("Тип", data.get("type")),
        ]
        for extra in data.get("extra", []):
            lines.append(kv("Данные", extra))
        return section(title, lines)

    # ── OK.ru ──
    if source_key == "ok":
        if not data.get("name"):
            return ""
        lines = [
            kv("Имя", data.get("name")),
            kv("Подписчиков", data.get("followers")),
            kv("Город", data.get("location")),
            kv("URL", f'<a href="{data.get("url", "")}">{data.get("url", "")}</a>'),
        ]
        return section(title, lines)

    # ── Instagram ──
    if source_key == "instagram":
        if not data.get("full_name") and not data.get("username"):
            return ""
        lines = [
            kv("Имя", data.get("full_name")),
            kv("Подписчики", data.get("followers")),
            kv("Подписки", data.get("following")),
            kv("Публикации", data.get("posts")),
            kv("Верифицирован", "✅" if data.get("verified") else "Нет"),
        ]
        return section(title, lines)

    # ── Twitter/X ──
    if source_key == "twitter":
        if not data.get("name") and not data.get("username"):
            return ""
        lines = [
            kv("Имя", data.get("name")),
            kv("Твиты", data.get("tweets")),
            kv("Подписчики", data.get("followers")),
            kv("Подписки", data.get("following")),
        ]
        return section(title, lines)

    # ── HIBP ──
    if source_key == "hibp":
        breaches = data.get("breaches") or (data if isinstance(data, list) else [])
        if not breaches:
            return ""
        lines = [f"Найдено утечек: <b>{len(breaches)}</b>\n"]
        for b in breaches[:5]:
            name = b.get("Name") or b.get("name", "?")
            lines.append(f"  🔸 {name}\n")
        return section(title, lines)

    # ── ЕГРЮЛ ──
    if source_key == "egrul":
        if not data.get("name") and not data.get("items"):
            return ""
        items = data.get("items") or ([data] if data.get("name") else [])
        lines = []
        for item in items[:3]:
            lines.append(kv("Название", item.get("name")))
            lines.append(kv("ИНН", item.get("inn")))
            lines.append(kv("ОГРН", item.get("ogrn")))
            lines.append(kv("Статус", item.get("status")))
            lines.append("\n")
        return section(title, lines)

    # ── WHOIS ──
    if source_key == "whois":
        if not data:
            return ""
        lines = [
            kv("Регистратор", data.get("registrar")),
            kv("Создан", data.get("creation_date")),
            kv("Истекает", data.get("expiration_date")),
        ]
        return section(title, lines)

    # ── DNS ──
    if source_key == "dns":
        if not data:
            return ""
        lines = []
        for rtype in ("A", "MX", "NS", "TXT"):
            records = data.get(rtype) or data.get(rtype.lower())
            if records:
                if isinstance(records, list):
                    lines.append(kv(rtype, ", ".join(str(r) for r in records[:3])))
                else:
                    lines.append(kv(rtype, str(records)))
        return section(title, lines)

    # ── IP геолокация ──
    if source_key == "geo":
        if not data:
            return ""
        lines = [
            kv("Страна", data.get("country")),
            kv("Город", data.get("city")),
            kv("Координаты", f"{data.get('lat')}, {data.get('lon')}" if data.get("lat") else None),
            kv("Провайдер", data.get("isp") or data.get("org")),
        ]
        return section(title, lines)

    # ── Поиск по ФИО (агрегат) ──
    if source_key == "fio":
        if not data:
            return ""
        # Результат fio_search — большой dict с ключами breach_lc, vk, hh и т.д.
        has_data = any(
            v and "error" not in (v if isinstance(v, dict) else {})
            for v in data.values()
        )
        if not has_data:
            return ""
        lines = []
        lc = data.get("breach_lc", {})
        if isinstance(lc, dict) and lc.get("found", 0):
            lines.append(f"LeakCheck: <b>{lc['found']}</b> записей\n")
        vk_d = data.get("vk", {})
        if isinstance(vk_d, dict) and vk_d.get("found", 0):
            lines.append(f"VK: <b>{vk_d['found']}</b> профилей\n")
        hh_d = data.get("hh", {})
        if isinstance(hh_d, dict) and hh_d.get("found", 0):
            lines.append(f"HH.ru: <b>{hh_d['found']}</b> резюме\n")
        if not lines:
            return ""
        return section(title, lines)

    # ── Автомобиль ГИБДД ──
    if source_key == "car":
        if not data:
            return ""
        lines = [
            kv("Марка/Модель", data.get("model") or data.get("brand")),
            kv("Год", data.get("year")),
            kv("Цвет", data.get("color")),
            kv("Ограничения", data.get("restrictions")),
            kv("Розыск", data.get("wanted")),
        ]
        tech = data.get("tech_inspection") or {}
        if isinstance(tech, dict) and tech.get("valid_until"):
            lines.append(kv("ТО до", tech["valid_until"]))
        return section(title, lines)

    # ── Паспорт ──
    if source_key == "passport":
        if not data:
            return ""
        lines = [
            kv("Статус", data.get("status")),
            kv("Действителен", "✅ Да" if data.get("valid") else "❌ Нет"),
        ]
        return section(title, lines)

    # ── Росреестр ──
    if source_key == "rosreestr":
        if not data:
            return ""
        lines = [
            kv("Адрес", data.get("address")),
            kv("Площадь", f"{data.get('area')} {data.get('area_unit', '')}" if data.get("area") else None),
            kv("Тип", data.get("type")),
            kv("Статус", data.get("status")),
        ]
        return section(title, lines)

    # Generic fallback — показываем непустые строковые поля
    lines = [kv(k, v) for k, v in data.items() if v and isinstance(v, (str, int, float)) and k != "url"]
    if not lines:
        return ""
    return section(source_key.upper(), lines)
