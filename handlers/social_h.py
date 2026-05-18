import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.vk_lookup import vk_user_lookup, vk_group_lookup
from modules.telegram_lookup import tg_user_lookup
from modules.ok_lookup import ok_user_lookup
from modules.instagram_lookup import instagram_lookup
from modules.twitter_lookup import twitter_lookup
from utils.formatter import kv, section, error_msg

router = Router()
log = logging.getLogger(__name__)


@router.message(Command("vk"))
async def cmd_vk(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "<code>/vk id123456789</code> — пользователь\n"
            "<code>/vk durov</code> — по screen_name\n"
            "<code>/vk club123</code> — группа",
            parse_mode="HTML",
        )
        return

    query = args[1].strip()
    msg = await message.answer(f"🔍 Ищу VK: <code>{query}</code>...", parse_mode="HTML")

    is_group = query.startswith(("club", "public", "event"))
    if is_group:
        data = await vk_group_lookup(query)
    else:
        data = await vk_user_lookup(query)

    if "error" in data:
        await msg.edit_text(error_msg(data["error"]), parse_mode="HTML")
        return

    if is_group:
        lines = [
            kv("ID", data.get("id")),
            kv("Название", data.get("name")),
            kv("Тип", data.get("type")),
            kv("Участников", data.get("members_count")),
            kv("Сайт", data.get("site")),
            kv("Верифицирован", "✅ Да" if data.get("verified") else "Нет"),
            kv("Статус", data.get("status")),
            kv("Город", data.get("city")),
        ]
        desc = data.get("description", "")
        if desc:
            lines.append(f"\n<b>Описание:</b>\n<i>{desc[:300]}</i>\n")
        text = f"👥 <b>VK Группа: {data.get('screen_name', query)}</b>\n"
        text += section("Информация", lines)
    else:
        profile_url = f"https://vk.com/{data.get('screen_name', 'id' + str(data.get('id', '')))}"
        lines = [
            kv("ID", data.get("id")),
            kv("Имя", data.get("name")),
            kv("Профиль", f'<a href="{profile_url}">{data.get("screen_name")}</a>'),
            kv("Дата рождения", data.get("bdate")),
            kv("Город", data.get("city")),
            kv("Страна", data.get("country")),
            kv("Подписчики", data.get("followers")),
            kv("Семейное положение", data.get("relation")),
            kv("Сайт", data.get("site")),
            kv("Последний визит", data.get("last_seen")),
            kv("Страница закрыта", "🔒 Да" if data.get("is_closed") else "🔓 Нет"),
            kv("Статус аккаунта", data.get("deactivated", "активен")),
        ]
        if data.get("status"):
            lines.append(f"\n<b>Статус:</b> <i>{data['status'][:200]}</i>\n")
        text = f"👤 <b>VK: {data.get('name', query)}</b>\n"
        text += section("Профиль", lines)

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("tg"))
async def cmd_tg(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: <code>/tg @username</code>", parse_mode="HTML"
        )
        return
    username = args[1].strip()
    msg = await message.answer(f"🔍 Ищу Telegram: <code>{username}</code>...", parse_mode="HTML")

    data = await tg_user_lookup(username)
    if "error" in data:
        await msg.edit_text(error_msg(data["error"]), parse_mode="HTML")
        return

    lines = [
        kv("Username", data.get("username")),
        kv("Имя", data.get("name")),
        kv("Тип", data.get("type")),
        kv("Описание", data.get("description", "")[:300] or None),
    ]
    for extra in data.get("extra", []):
        lines.append(kv("Данные", extra))

    text = f"✈️ <b>Telegram: {data.get('name', username)}</b>\n"
    text += section("Профиль", lines)
    if data.get("url"):
        text += f'\n<a href="{data["url"]}">Открыть профиль</a>'

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=False)


@router.message(Command("ok"))
async def cmd_ok(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование:\n"
            "  <code>/ok odnoklassniki</code> — по username\n"
            "  <code>/ok 123456789</code> — по числовому ID\n\n"
            "Источник: OK.ru (публичные профили)",
            parse_mode="HTML",
        )
        return

    query = args[1].strip()
    log.debug("cmd_ok: запрос %r от user_id=%s", query, message.from_user.id if message.from_user else "?")
    msg = await message.answer(f"🔍 Ищу OK.ru: <code>{query}</code>...", parse_mode="HTML")

    data = await ok_user_lookup(query)
    if "error" in data:
        await msg.edit_text(error_msg(data["error"]), parse_mode="HTML")
        return

    lines = [
        kv("Имя", data.get("name")),
        kv("Подписчиков", data.get("followers")),
        kv("Город", data.get("location")),
        kv("Профиль", f'<a href="{data.get("url", "")}">{data.get("url", "")}</a>'),
    ]
    if data.get("bio"):
        lines.append(f"\n<b>О себе:</b> <i>{data['bio'][:200]}</i>\n")

    text = f"🟠 <b>OK.ru: {data.get('name', query)}</b>\n"
    text += section("Профиль", lines)

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("inst"))
async def cmd_inst(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: <code>/inst instagram</code>\n\n"
            "Источник: Instagram публичные профили (без авторизации)",
            parse_mode="HTML",
        )
        return

    username = args[1].strip().lstrip("@")
    log.debug("cmd_inst: запрос %r от user_id=%s", username, message.from_user.id if message.from_user else "?")
    msg = await message.answer(f"🔍 Ищу Instagram: <code>@{username}</code>...", parse_mode="HTML")

    data = await instagram_lookup(username)
    if "error" in data and not data.get("full_name"):
        await msg.edit_text(error_msg(data["error"]), parse_mode="HTML")
        return

    verified_str = "✅ Да" if data.get("verified") else "Нет"
    private_str = "🔒 Да" if data.get("private") else "🔓 Нет"
    lines = [
        kv("Username", f"@{data.get('username', username)}"),
        kv("Имя", data.get("full_name")),
        kv("Подписчики", data.get("followers")),
        kv("Подписки", data.get("following")),
        kv("Публикации", data.get("posts")),
        kv("Верифицирован", verified_str),
        kv("Приватный", private_str),
        kv("Сайт", data.get("external_url")),
    ]
    if data.get("bio"):
        lines.append(f"\n<b>Bio:</b> <i>{data['bio'][:200]}</i>\n")

    text = f"📸 <b>Instagram: @{data.get('username', username)}</b>\n"
    text += section("Профиль", lines)
    if data.get("url"):
        text += f'\n<a href="{data["url"]}">Открыть профиль</a>'

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("tw"))
async def cmd_tw(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: <code>/tw elonmusk</code>\n\n"
            "Источник: Nitter (зеркала Twitter/X без ключа)",
            parse_mode="HTML",
        )
        return

    username = args[1].strip().lstrip("@")
    log.debug("cmd_tw: запрос %r от user_id=%s", username, message.from_user.id if message.from_user else "?")
    msg = await message.answer(f"🔍 Ищу Twitter/X: <code>@{username}</code>...", parse_mode="HTML")

    data = await twitter_lookup(username)
    if "error" in data and not data.get("name"):
        await msg.edit_text(
            error_msg(data["error"]) + f'\n\n<a href="https://x.com/{username}">Открыть X.com</a>',
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    verified_str = "✅ Да" if data.get("verified") else "Нет"
    lines = [
        kv("Username", f"@{data.get('username', username)}"),
        kv("Имя", data.get("name")),
        kv("Твиты", data.get("tweets")),
        kv("Подписчики", data.get("followers")),
        kv("Подписки", data.get("following")),
        kv("Дата регистрации", data.get("joined")),
        kv("Верифицирован", verified_str),
    ]
    if data.get("bio"):
        lines.append(f"\n<b>Bio:</b> <i>{data['bio'][:200]}</i>\n")
    if data.get("source"):
        lines.append(f"\n<i>Источник: {data['source']}</i>\n")

    text = f"🐦 <b>Twitter/X: @{data.get('username', username)}</b>\n"
    text += section("Профиль", lines)
    if data.get("url"):
        text += f'\n<a href="{data["url"]}">Открыть профиль</a>'

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
