import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand
from aiogram.enums import ParseMode

from config import BOT_TOKEN, ALLOWED_USERS
from handlers import (
    domain_router, email_router, phone_router,
    username_router, social_router, image_router,
    breach_router, fio_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Middleware для ограничения доступа
    if ALLOWED_USERS:
        @dp.message.outer_middleware()
        async def access_control(handler, event: Message, data):
            if event.from_user and event.from_user.id not in ALLOWED_USERS:
                await event.answer("⛔ Доступ запрещён.")
                return
            return await handler(event, data)

    dp.include_routers(
        domain_router,
        email_router,
        phone_router,
        username_router,
        social_router,
        image_router,
        breach_router,
        fio_router,
    )
    return dp


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Список команд"),
        BotCommand(command="domain", description="WHOIS + DNS + субдомены"),
        BotCommand(command="ip", description="Геолокация IP"),
        BotCommand(command="email", description="Проверка email + утечки"),
        BotCommand(command="phone", description="Информация о номере"),
        BotCommand(command="user", description="Поиск username по сайтам"),
        BotCommand(command="vk", description="VK профиль / группа"),
        BotCommand(command="tg", description="Telegram профиль"),
        BotCommand(command="photo", description="Реверс-поиск по фото"),
        BotCommand(command="breach", description="Пробив по базам утечек"),
        BotCommand(command="fio", description="Поиск по ФИО"),
    ]
    await bot.set_my_commands(commands)


async def main():
    if not BOT_TOKEN:
        log.error("BOT_TOKEN не задан! Скопируй .env.example в .env и заполни.")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        await message.answer(
            "🕵️ <b>OSINT Bot</b>\n\n"
            "Команды:\n"
            "/domain <code>example.com</code> — WHOIS, DNS, субдомены\n"
            "/ip <code>8.8.8.8</code> — геолокация IP\n"
            "/email <code>user@example.com</code> — проверка email + утечки\n"
            "/phone <code>+79001234567</code> — информация о номере\n"
            "/user <code>nickname</code> — поиск username по 35+ сайтам\n"
            "/vk <code>durov</code> — VK профиль\n"
            "/tg <code>@username</code> — Telegram профиль\n"
            "/breach <code>email user@x.com</code> — пробив по базам утечек\n"
            "/fio <code>Иванов Иван [Отч]</code> — поиск по ФИО\n"
            "📷 <b>Отправьте фото</b> — реверс-поиск через Yandex\n\n"
            "<i>⚠️ Используй только для авторизованного тестирования.</i>",
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        await cmd_start(message)

    await set_commands(bot)
    log.info("Бот запущен")
    await dp.start_polling(bot, allowed_updates=["message"])


if __name__ == "__main__":
    asyncio.run(main())
