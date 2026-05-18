import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.address_lookup import address_search, rosreestr_lookup, is_cadastral
from utils.formatter import kv, section, error_msg

router = Router()
log = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>/address</b> — Поиск адреса и кадастровых данных\n\n"
    "Использование:\n"
    "  <code>/address Москва Тверская 1</code> — поиск адреса (ФИАС + 2GIS)\n"
    "  <code>/address 77:01:0001001:1</code> — кадастровый номер (Росреестр)\n\n"
    "Источники: ФИАС · 2GIS · Росреестр ПКК"
)


@router.message(Command("address"))
async def cmd_address(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    query = args[1].strip()
    log.debug("cmd_address: запрос %r от user_id=%s", query, message.from_user.id if message.from_user else "?")

    if is_cadastral(query):
        # Кадастровый номер → Росреестр
        msg = await message.answer(
            f"🔍 Запрашиваю Росреестр ПКК: <code>{query}</code>...",
            parse_mode="HTML",
        )
        log.debug("cmd_address: кадастровый номер %r", query)
        data = await rosreestr_lookup(query)

        if "error" in data:
            await msg.edit_text(error_msg(data["error"]), parse_mode="HTML")
            return

        lines = [
            kv("Кадастровый №", data.get("cadastral")),
            kv("Адрес", data.get("address")),
            kv("Площадь", f"{data.get('area')} {data.get('area_unit', '')}" if data.get("area") else None),
            kv("Тип", data.get("type")),
            kv("Статус", data.get("status")),
            kv("Кадастровая стоимость", data.get("cost")),
            kv("Дата оценки", data.get("date")),
        ]
        text = f"🏠 <b>Росреестр ПКК: {query}</b>\n"
        text += section("Объект недвижимости", lines)

    else:
        # Поиск адреса
        msg = await message.answer(
            f"🔍 Ищу адрес: <code>{query}</code>...",
            parse_mode="HTML",
        )
        log.debug("cmd_address: поиск адреса %r", query)
        data = await address_search(query)

        if "error" in data:
            await msg.edit_text(error_msg(data["error"]), parse_mode="HTML")
            return

        results = data.get("results", [])
        found = data.get("found", 0)

        if not results:
            await msg.edit_text(
                f"🔍 Адрес <code>{query}</code> не найден.",
                parse_mode="HTML",
            )
            return

        text = f"📍 <b>Поиск адреса: {query}</b>\n"
        text += f"\n<i>Найдено: {found} результатов</i>\n"

        for i, item in enumerate(results[:8], 1):
            source = item.get("source", "")
            addr = item.get("address", "")
            coords = ""
            if item.get("lat") and item.get("lon"):
                coords = f" <i>[{item['lat']}, {item['lon']}]</i>"
            fias_id = ""
            if item.get("fias_id"):
                fias_id = f"\n    ФИАС ID: <code>{item['fias_id']}</code>"
            text += f"\n{i}. [{source}] <code>{addr}</code>{coords}{fias_id}\n"

    if len(text) > 4000:
        text = text[:3980] + "\n\n<i>… обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
