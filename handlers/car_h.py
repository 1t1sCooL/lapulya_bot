import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.car_lookup import car_check, normalize_plate
from utils.formatter import kv, section, error_msg

router = Router()
log = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>/car</b> — Пробив госномера автомобиля\n\n"
    "Использование:\n"
    "  <code>/car А123БВ77</code>\n"
    "  <code>/car A123BV77</code>  — латинские буквы тоже принимаются\n\n"
    "Проверяется: ограничения · розыск · техосмотр (ЕАИСТО)\n"
    "Источник: ГИБДД (без ключа)"
)


def _fmt_eaisto(eaisto: dict | None) -> str:
    if not eaisto or not isinstance(eaisto, dict):
        return ""

    lines = []

    # Пытаемся извлечь самые интересные поля
    # Структура ЕАИСТО может меняться — выводим всё что есть
    def _extract(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    _extract(v, f"{prefix}{k}.")
                elif v is not None and str(v).strip() not in ("", "null", "None"):
                    lines.append(kv(f"{prefix}{k}", str(v)))
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:3]):
                _extract(item, f"{prefix}[{i}].")

    _extract(eaisto)

    if not lines:
        return ""
    return section("Техосмотр (ЕАИСТО)", lines)


@router.message(Command("car"))
async def cmd_car(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    raw_plate = args[1].strip()
    user_id = message.from_user.id if message.from_user else "?"
    log.debug("cmd_car: запрос %r от user_id=%s", raw_plate, user_id)

    plate_display = normalize_plate(raw_plate)

    msg = await message.answer(
        f"🚗 Проверяю номер <b>{plate_display}</b>...",
        parse_mode="HTML",
    )

    result = await car_check(raw_plate)
    log.debug("cmd_car: проверка завершена для %r", raw_plate)

    if "error" in result:
        log.error("cmd_car: ошибка для %r: %s", raw_plate, result["error"])
        await msg.edit_text(error_msg(result["error"]), parse_mode="HTML")
        return

    plate = result.get("plate", plate_display)
    restrictions = result.get("restrictions", [])
    wanted = result.get("wanted", False)
    gibdd_unavailable = result.get("gibdd_captcha", False)
    eaisto = result.get("eaisto")

    # Заголовок
    text = f"🚗 <b>Госномер: {plate}</b>\n"

    # Блок ГИБДД
    gibdd_lines = []

    if gibdd_unavailable:
        gibdd_lines.append("⚠️ ГИБДД недоступен (CAPTCHA) — попробуйте позже\n")
    else:
        if wanted:
            gibdd_lines.append("🚨 <b>АВТОМОБИЛЬ В РОЗЫСКЕ</b>\n")
        else:
            gibdd_lines.append("✅ В розыске не значится\n")

        if restrictions:
            gibdd_lines.append(f"⚠️ Ограничений: <b>{len(restrictions)}</b>\n")
            for r in restrictions[:10]:
                gibdd_lines.append(f"  • <code>{r}</code>\n")
        else:
            gibdd_lines.append("✅ Ограничений не обнаружено\n")

    text += section("ГИБДД", gibdd_lines)

    # Блок ЕАИСТО
    eaisto_section = _fmt_eaisto(eaisto)
    if eaisto_section:
        text += eaisto_section
    elif eaisto is None:
        text += section("Техосмотр (ЕАИСТО)", ["⚠️ Данные недоступны\n"])

    if len(text) > 4000:
        text = text[:3980] + "\n\n<i>… обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
