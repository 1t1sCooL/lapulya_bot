import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from modules.egrul import egrul_search
from utils.formatter import kv, section, error_msg

router = Router()
log = logging.getLogger(__name__)

HELP_TEXT = (
    "<b>/company</b> — Поиск ЮЛ/ИП по ИНН, ОГРН или наименованию\n\n"
    "Использование:\n"
    "  <code>/company 7707083893</code>  — по ИНН\n"
    "  <code>/company 1027700132195</code>  — по ОГРН\n"
    "  <code>/company Сбербанк</code>  — по названию\n\n"
    "Источник: ФНС ЕГРЮЛ/ЕГРИП (без ключа)"
)

_MAX_RESULTS = 5


def _fmt_company(rec: dict, idx: int) -> str:
    name = rec.get("name") or rec.get("short_name") or "—"
    short = rec.get("short_name", "")
    title = f"🏢 <b>{idx}. {name}</b>\n"
    if short and short != name:
        title = f"🏢 <b>{idx}. {short}</b>\n<i>{name}</i>\n"

    lines = [
        title,
        kv("ИНН", rec.get("inn")),
        kv("ОГРН", rec.get("ogrn")),
        kv("Тип", rec.get("kind")),
        kv("Адрес", rec.get("address")),
        kv("Статус", rec.get("status")),
    ]
    return "".join(l for l in lines if l)


@router.message(Command("company"))
async def cmd_company(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(HELP_TEXT, parse_mode="HTML")
        return

    query = args[1].strip()
    user_id = message.from_user.id if message.from_user else "?"
    log.debug("cmd_company: запрос %r от user_id=%s", query, user_id)

    msg = await message.answer(
        f"🔍 Ищу <b>{query}</b> в ЕГРЮЛ/ЕГРИП...",
        parse_mode="HTML",
    )

    result = await egrul_search(query)
    log.debug("cmd_company: поиск завершён для %r", query)

    if "error" in result:
        log.error("cmd_company: ошибка для %r: %s", query, result["error"])
        await msg.edit_text(error_msg(result["error"]), parse_mode="HTML")
        return

    found = result.get("found", 0)
    rows = result.get("results", [])

    if not found or not rows:
        await msg.edit_text(
            f"🔍 Ничего не найдено для <code>{query}</code>",
            parse_mode="HTML",
        )
        return

    shown = rows[:_MAX_RESULTS]
    header = f"🏛 <b>ЕГРЮЛ/ЕГРИП: {query}</b> — найдено {found}\n"

    blocks = []
    for i, rec in enumerate(shown, start=1):
        blocks.append(_fmt_company(rec, i))

    body = "\n".join(blocks)

    if found > _MAX_RESULTS:
        body += f"\n<i>...показано {_MAX_RESULTS} из {found}</i>"

    text = header + "\n" + body

    if len(text) > 4000:
        text = text[:3980] + "\n\n<i>… обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
