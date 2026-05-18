import logging
import re
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.doc_lookup import check_passport, find_inn, validate_inn
from utils.formatter import kv, section, error_msg

router = Router()
log = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>/doc</b> — Проверка документов\n\n"
    "Использование:\n"
    "  <code>/doc паспорт 4510 123456</code>  — проверка паспорта РФ\n"
    "  <code>/doc инн Иванов Иван Иванович 01.01.1990</code>  — ИНН по ФИО\n"
    "  <code>/doc валидация 770112345678</code>  — проверка контрольной суммы ИНН\n\n"
    "Источники: МВД (паспорт) · ФНС (ИНН)"
)

# Подкоманды
_CMD_PASSPORT = {"паспорт", "passport", "п"}
_CMD_INN = {"инн", "inn", "и"}
_CMD_VALIDATE = {"валидация", "validate", "проверить", "в"}


@router.message(Command("doc"))
async def cmd_doc(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    rest = args[1].strip()
    parts = rest.split(maxsplit=1)
    subcmd = parts[0].lower()
    body = parts[1].strip() if len(parts) > 1 else ""

    user_id = message.from_user.id if message.from_user else "?"
    log.debug("cmd_doc: subcmd=%r body=%r user_id=%s", subcmd, body, user_id)

    if subcmd in _CMD_PASSPORT:
        await _handle_passport(message, body)
    elif subcmd in _CMD_INN:
        await _handle_inn(message, body)
    elif subcmd in _CMD_VALIDATE:
        await _handle_validate(message, body)
    else:
        await message.answer(
            f"⚠️ Неизвестная подкоманда <code>{subcmd}</code>.\n\n" + HELP_TEXT,
            parse_mode="HTML",
        )


# ---------------------------------------------------------------------------
# Паспорт
# ---------------------------------------------------------------------------

async def _handle_passport(message: Message, body: str):
    """
    /doc паспорт <серия> <номер>
    Серия — 4 цифры, номер — 6 цифр. Пробел между ними допустим.
    """
    body = body.strip()

    # Парсим серию и номер: "4510 123456", "4510123456"
    m = re.fullmatch(r"(\d{4})\s*(\d{6})", body)
    if not m:
        await message.answer(
            "⚠️ Укажи серию (4 цифры) и номер (6 цифр).\n"
            "Пример: <code>/doc паспорт 4510 123456</code>",
            parse_mode="HTML",
        )
        return

    series, number = m.group(1), m.group(2)
    log.debug("_handle_passport: серия=%r номер=%r", series, number)

    msg = await message.answer(
        f"🔍 Проверяю паспорт <b>{series} {number}</b>...",
        parse_mode="HTML",
    )

    result = await check_passport(series, number)
    log.debug("_handle_passport: результат %s", result)

    valid = result.get("valid")
    status = result.get("status", "неизвестно")

    if valid is True:
        icon = "✅"
    elif valid is False:
        icon = "❌"
    else:
        icon = "⚠️"

    text = (
        f"🪪 <b>Паспорт РФ: {series} {number}</b>\n\n"
        f"{icon} <b>{status.capitalize()}</b>\n"
    )

    if valid is None:
        text += "\n<i>Сервис МВД может быть временно недоступен или требует CAPTCHA.</i>"

    await msg.edit_text(text, parse_mode="HTML")


# ---------------------------------------------------------------------------
# ИНН по ФИО
# ---------------------------------------------------------------------------

async def _handle_inn(message: Message, body: str):
    """
    /doc инн <Фамилия> <Имя> [Отчество] <дд.мм.гггг>
    Дата рождения — последний аргумент.
    """
    body = body.strip()
    # Дата — последнее слово формата дд.мм.гггг
    m = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*$", body)
    if not m:
        await message.answer(
            "⚠️ Укажи ФИО и дату рождения.\n"
            "Пример: <code>/doc инн Иванов Иван Иванович 01.01.1990</code>",
            parse_mode="HTML",
        )
        return

    birthdate = m.group(1)
    fio_str = body[: m.start()].strip()
    fio_parts = fio_str.split()

    if len(fio_parts) < 2:
        await message.answer(
            "⚠️ Укажи минимум Фамилию и Имя.\n"
            "Пример: <code>/doc инн Иванов Иван 01.01.1990</code>",
            parse_mode="HTML",
        )
        return

    last = fio_parts[0]
    first = fio_parts[1]
    middle = fio_parts[2] if len(fio_parts) >= 3 else ""
    display = f"{last} {first}" + (f" {middle}" if middle else "")

    log.debug("_handle_inn: ФИО=%r дата=%r", display, birthdate)

    msg = await message.answer(
        f"🔍 Ищу ИНН для <b>{display}</b>, {birthdate}...",
        parse_mode="HTML",
    )

    result = await find_inn(last, first, middle, birthdate)
    log.debug("_handle_inn: результат %s", result)

    if "error" in result:
        await msg.edit_text(
            f"👤 <b>ИНН: {display}</b>\n\n"
            f"⚠️ {result['error']}",
            parse_mode="HTML",
        )
        return

    inn = result.get("inn", "")
    text = (
        f"👤 <b>ИНН: {display}</b>, {birthdate}\n\n"
        f"✅ ИНН: <code>{inn}</code>\n"
    )

    # Дополнительно валидируем найденный ИНН
    if inn and not validate_inn(inn):
        text += "\n⚠️ <i>Примечание: контрольная сумма ИНН не сходится</i>"

    await msg.edit_text(text, parse_mode="HTML")


# ---------------------------------------------------------------------------
# Валидация ИНН
# ---------------------------------------------------------------------------

async def _handle_validate(message: Message, body: str):
    """
    /doc валидация <ИНН>
    Проверяет контрольную сумму ИНН алгоритмом — без сетевых запросов.
    """
    inn = body.strip().replace(" ", "")

    if not inn:
        await message.answer(
            "⚠️ Укажи ИНН для проверки.\n"
            "Пример: <code>/doc валидация 770112345678</code>",
            parse_mode="HTML",
        )
        return

    if not inn.isdigit():
        await message.answer(
            error_msg("ИНН должен содержать только цифры."),
            parse_mode="HTML",
        )
        return

    log.debug("_handle_validate: ИНН=%r длина=%d", inn, len(inn))

    length = len(inn)
    if length not in (10, 12):
        await message.answer(
            f"⚠️ ИНН должен содержать 10 (ЮЛ) или 12 (ФЛ) цифр.\n"
            f"Вы ввели: <code>{inn}</code> ({length} цифр)",
            parse_mode="HTML",
        )
        return

    is_valid = validate_inn(inn)
    kind = "ЮЛ (10 цифр)" if length == 10 else "ФЛ (12 цифр)"

    if is_valid:
        text = (
            f"🔢 <b>Валидация ИНН</b>\n\n"
            f"✅ <code>{inn}</code>\n"
            f"Тип: {kind}\n"
            f"Контрольная сумма: верна"
        )
    else:
        text = (
            f"🔢 <b>Валидация ИНН</b>\n\n"
            f"❌ <code>{inn}</code>\n"
            f"Тип: {kind}\n"
            f"Контрольная сумма: <b>не совпадает</b> — ИНН некорректен"
        )

    await message.answer(text, parse_mode="HTML")
