import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.username_lookup import username_search_stream, site_count
from modules.sites_data import SITES

router = Router()

# Интервал обновления сообщения (сек) — не чаще раза в 2 секунды (Telegram rate limit)
UPDATE_INTERVAL = 2.5


@router.message(Command("user", "username"))
async def cmd_username(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: <code>/user nickname</code>", parse_mode="HTML"
        )
        return

    username = args[1].strip().lstrip("@")
    total_sites = site_count()

    msg = await message.answer(
        f"🔍 Поиск <code>{username}</code> по <b>{total_sites}</b> сайтам...\n"
        f"<i>Найдено: 0 | Проверено: 0/{total_sites}</i>",
        parse_mode="HTML",
    )

    found: list[dict] = []
    checked = 0
    last_update = asyncio.get_event_loop().time()

    async def update_progress():
        nonlocal last_update
        now = asyncio.get_event_loop().time()
        if now - last_update < UPDATE_INTERVAL:
            return
        last_update = now
        preview = "\n".join(
            f"  🟢 <a href='{r['url']}'>{r['site']}</a>"
            for r in found[-5:]
        )
        await msg.edit_text(
            f"🔍 Поиск <code>{username}</code> по <b>{total_sites}</b> сайтам...\n"
            f"<i>Найдено: {len(found)} | Проверено: {checked}/{total_sites}</i>\n"
            + (f"\nПоследние находки:\n{preview}" if found else ""),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    async for result in username_search_stream(username):
        checked += 1
        found.append(result)
        await update_progress()

    # Финальное сообщение
    if not found:
        await msg.edit_text(
            f"🔍 <b>Username: {username}</b>\n\n"
            f"Не найдено ни на одном из {total_sites} сайтов.",
            parse_mode="HTML",
        )
        return

    # Группируем по категориям
    categories = _categorize(found)
    lines = [f"👤 <b>Username: {username}</b> — найден на <b>{len(found)}</b> сайтах\n"]

    for cat, items in sorted(categories.items()):
        lines.append(f"\n<b>{cat}</b>")
        for r in items:
            lines.append(f"  🟢 <a href='{r['url']}'>{r['site']}</a>")

    text = "\n".join(lines)
    # Telegram лимит 4096
    if len(text) > 4000:
        text = text[:3980] + "\n\n<i>... обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)


def _categorize(results: list[dict]) -> dict[str, list[dict]]:
    """Раскладываем результаты по категориям на основе имени сайта."""
    category_map = {
        "Разработка": {"GitHub", "GitLab", "Bitbucket", "SourceForge", "CodePen", "Replit",
                       "JSFiddle", "Kaggle", "HackerEarth", "HackerRank", "LeetCode",
                       "Codewars", "CodinGame", "npm", "PyPI", "DockerHub", "RubyGems",
                       "crates.io", "Packagist", "Gitea", "Stack Overflow"},
        "Соцсети": {"Twitter/X", "Instagram", "Facebook", "TikTok", "Pinterest", "Reddit",
                    "Tumblr", "VK", "OK.ru", "Mastodon", "Telegram", "LinkedIn",
                    "Snapchat", "Discord", "Clubhouse", "MeWe", "Minds", "Gab", "Parler"},
        "Видео / Стриминг": {"YouTube", "Twitch", "Vimeo", "DailyMotion", "Trovo",
                              "Odysee", "Rumble", "Kick", "PeerTube"},
        "Музыка": {"SoundCloud", "Spotify", "Last.fm", "Bandcamp", "Mixcloud",
                   "ReverbNation", "Audiomack", "Tidal"},
        "Игры": {"Steam", "Chess.com", "Lichess", "Roblox", "Minecraft", "Battlenet",
                 "Kongregate", "Newgrounds", "Itch.io", "GameBanana", "SpeedRunsLive",
                 "Speedrun.com", "Faceit"},
        "Арт / Фото": {"Flickr", "500px", "Behance", "Dribbble", "DeviantArt", "ArtStation",
                       "Unsplash", "PixelFed", "Imgur", "GuruShots", "Wattpad",
                       "Fur Affinity", "Cara"},
        "Блоги / Контент": {"Medium", "Dev.to", "Hashnode", "Substack", "WordPress", "Ghost",
                             "Blogger", "Livejournal", "Quora", "HackerNews", "Lobsters",
                             "Lemmy", "Hubpages"},
        "Фриланс / Бизнес": {"ProductHunt", "AngelList", "Crunchbase", "Wellfound",
                              "Indie Hackers", "Freelancer", "Fiverr", "Upwork", "Guru",
                              "PeoplePerHour", "Toptal"},
        "Профиль / Identity": {"Keybase", "Gravatar", "About.me", "Linktree", "Carrd",
                                "Bento", "Beacons", "Bio.link", "Biolinks",
                                "Patreon", "Ko-fi", "Buy Me a Coffee", "Gumroad"},
        "Другое": set(),
    }

    # Инвертируем карту
    site_to_cat: dict[str, str] = {}
    for cat, names in category_map.items():
        for n in names:
            site_to_cat[n] = cat

    out: dict[str, list[dict]] = {}
    for r in results:
        cat = site_to_cat.get(r["site"], "Другое")
        out.setdefault(cat, []).append(r)

    return {k: v for k, v in out.items() if v}
