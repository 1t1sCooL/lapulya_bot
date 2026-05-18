from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.phone_lookup import parse_phone
from utils.formatter import kv, section, error_msg

router = Router()


@router.message(Command("phone"))
async def cmd_phone(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: <code>/phone +79001234567</code>", parse_mode="HTML"
        )
        return

    number = args[1].strip()
    result = parse_phone(number)

    if "error" in result:
        await message.answer(error_msg(result["error"]), parse_mode="HTML")
        return

    valid_icon = "✅" if result["valid"] else "⚠️"
    lines = [
        kv("Номер (E.164)", result.get("e164")),
        kv("Международный", result.get("international")),
        kv("Национальный", result.get("national")),
        kv("Страна/Регион", result.get("region")),
        kv("Оператор", result.get("carrier") or "Неизвестно"),
        kv("Тип", result.get("number_type")),
        kv("Часовые пояса", ", ".join(result.get("timezones", []))),
        kv("Валидный", f"{valid_icon} {'Да' if result['valid'] else 'Нет'}"),
    ]

    text = f"📱 <b>OSINT: {number}</b>\n"
    text += section("Информация о номере", lines)
    await message.answer(text, parse_mode="HTML")
