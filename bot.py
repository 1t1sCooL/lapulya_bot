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
    company_router, car_router, doc_router,
    address_router, osint_router, tools_router,
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
        tools_router,      # отдельные сервисы — первым (короткие команды)
        domain_router,
        email_router,
        phone_router,
        username_router,
        social_router,
        image_router,
        breach_router,
        fio_router,
        company_router,
        car_router,
        doc_router,
        address_router,
        osint_router,
    )
    return dp


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start",      description="Главное меню и список команд"),
        # ── Агрегаторы ──
        BotCommand(command="osint",      description="Сводный OSINT (авто-определение типа)"),
        BotCommand(command="email",      description="Полный OSINT по email"),
        BotCommand(command="phone",      description="Полный OSINT по номеру телефона"),
        BotCommand(command="user",       description="Поиск username: Sherlock+Maigret+WMN"),
        BotCommand(command="domain",     description="WHOIS + DNS + субдомены + Hunter"),
        BotCommand(command="ip",         description="IP: гео + Shodan + GreyNoise + AbuseIPDB"),
        BotCommand(command="breach",     description="Пробив по базам утечек (все источники)"),
        # ── Соцсети ──
        BotCommand(command="vk",         description="VK профиль / группа"),
        BotCommand(command="tg",         description="Telegram профиль / канал"),
        BotCommand(command="ok",         description="OK.ru профиль"),
        BotCommand(command="inst",       description="Instagram профиль"),
        BotCommand(command="tw",         description="Twitter/X профиль"),
        # ── Данные ──
        BotCommand(command="fio",        description="Поиск по ФИО"),
        BotCommand(command="company",    description="ЮЛ/ИП по ИНН/ОГРН (ЕГРЮЛ)"),
        BotCommand(command="car",        description="Госномер автомобиля"),
        BotCommand(command="doc",        description="Паспорт / ИНН физлица"),
        BotCommand(command="address",    description="Адрес / кадастровый номер"),
        # ── Отдельные сервисы ──
        BotCommand(command="wa",         description="WhatsApp: регистрация номера"),
        BotCommand(command="htmlweb",    description="htmlweb.ru: оператор и регион номера"),
        BotCommand(command="wayback",    description="Wayback Machine: история сайта"),
        BotCommand(command="wmn",        description="WhatsMyName: 1500+ сайтов для username"),
        BotCommand(command="maigret",    description="Maigret: 3000+ сайтов для username"),
        BotCommand(command="holehe",     description="Holehe: 144 сервиса по email"),
        BotCommand(command="hibp",       description="HIBP: Have I Been Pwned"),
        BotCommand(command="xon",        description="XposedOrNot: 400+ баз утечек"),
        BotCommand(command="proxynova",  description="Proxynova COMB: 3.2 млрд пар"),
        BotCommand(command="leakcheck",  description="LeakCheck public: источники утечек"),
        BotCommand(command="intelx",     description="IntelX: пасты и дампы"),
        BotCommand(command="hudsonrock", description="HudsonRock: инфостилеры"),
        BotCommand(command="sfs",        description="StopForumSpam: база спамеров"),
        BotCommand(command="torcheck",   description="Tor check: exit node проверка"),
        BotCommand(command="crack",      description="Взлом хэша MD5/SHA1/SHA256"),
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

            "━━ <b>АГРЕГАТОРЫ</b> ━━\n"
            "/osint <code>запрос</code> — авто-определение типа, всё сразу\n"
            "/email <code>user@mail.ru</code> — Holehe+HIBP+XON+LeakCheck+HudsonRock+Proxynova\n"
            "/phone <code>+79001234567</code> — NumVerify+htmlweb+GetContact+утечки\n"
            "/user <code>nickname</code> — Sherlock+Maigret+WhatsMyName (3500+ сайтов)\n"
            "/domain <code>example.com</code> — WHOIS+DNS+субдомены+Hunter email\n"
            "/ip <code>8.8.8.8</code> — гео+Shodan+GreyNoise+AbuseIPDB+Tor\n"
            "/breach <code>email user@x.com</code> — все базы утечек\n\n"

            "━━ <b>СОЦСЕТИ</b> ━━\n"
            "/vk <code>durov</code> — профиль ВКонтакте\n"
            "/tg <code>@username</code> — профиль / канал Telegram\n"
            "/ok <code>username</code> — OK.ru профиль\n"
            "/inst <code>username</code> — Instagram профиль\n"
            "/tw <code>elonmusk</code> — Twitter/X профиль\n\n"

            "━━ <b>ДАННЫЕ</b> ━━\n"
            "/fio <code>Иванов Иван Иванович</code> — поиск по ФИО\n"
            "/company <code>7707083893</code> — ЮЛ/ИП по ИНН/ОГРН\n"
            "/car <code>А123БВ77</code> — госномер авто\n"
            "/doc <code>паспорт 4510 123456</code> — паспорт / ИНН\n"
            "/address <code>Москва Тверская 1</code> — адрес / кадастр\n\n"

            "━━ <b>ОТДЕЛЬНЫЕ СЕРВИСЫ</b> ━━\n"
            "<b>Телефон:</b>\n"
            "  /wa <code>+79001234567</code> — WhatsApp регистрация\n"
            "  /htmlweb <code>+7900...</code> — оператор и регион (htmlweb.ru)\n\n"

            "<b>Email:</b>\n"
            "  /holehe <code>u@mail.ru</code> — 144 сервиса где зарегистрирован\n"
            "  /hibp <code>u@mail.ru</code> — Have I Been Pwned\n"
            "  /xon <code>u@mail.ru</code> — XposedOrNot 400+ баз\n"
            "  /leakcheck <code>u@mail.ru</code> — LeakCheck источники\n\n"

            "<b>Username:</b>\n"
            "  /wmn <code>nick</code> — WhatsMyName 1500+ сайтов\n"
            "  /maigret <code>nick</code> — Maigret 3000+ сайтов\n\n"

            "<b>Утечки:</b>\n"
            "  /proxynova <code>email</code> — Proxynova COMB 3.2B\n"
            "  /intelx <code>query</code> — IntelX пасты и дампы\n"
            "  /hudsonrock <code>email/username/domain query</code> — инфостилеры\n"
            "  /crack <code>хэш</code> — взлом MD5/SHA1/SHA256\n\n"

            "<b>Домен / IP:</b>\n"
            "  /wayback <code>example.com</code> — история в Wayback Machine\n"
            "  /torcheck <code>1.2.3.4</code> — Tor exit node проверка\n"
            "  /sfs <code>email/ip/username запрос</code> — StopForumSpam\n\n"

            "📷 <b>Отправь фото</b> — реверс-поиск Yandex + Face++\n\n"
            "<i>⚠️ Только для авторизованного тестирования.</i>",
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        await cmd_start(message)

    await set_commands(bot)
    log.info("Бот запущен")
    await dp.start_polling(bot, allowed_updates=["message"])


if __name__ == "__main__":
    asyncio.run(main())
