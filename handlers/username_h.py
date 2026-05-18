import asyncio
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from modules.username_lookup import username_search_stream, site_count
from modules.maigret_lookup import maigret_search, group_by_category
from modules.stopforumspam import sfs_check

router = Router()
log = logging.getLogger(__name__)

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
        f"🔍 Поиск <code>{username}</code>...\n"
        f"<i>Запущено: собственная база ({total_sites} сайтов) + Maigret (3000+)</i>",
        parse_mode="HTML",
    )

    # Запускаем Maigret и StopForumSpam параллельно с собственным поиском
    maigret_task = asyncio.create_task(maigret_search(username))
    sfs_task = asyncio.create_task(sfs_check(username, "username"))

    # Собственный потоковый поиск
    found_local: list[dict] = []
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
            for r in found_local[-5:]
        )
        try:
            await msg.edit_text(
                f"🔍 Поиск <code>{username}</code>...\n"
                f"<i>Своя база: найдено {len(found_local)} / проверено {checked}/{total_sites}</i>\n"
                + (f"\nПоследние:\n{preview}" if found_local else ""),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            pass

    async for result in username_search_stream(username):
        checked += 1
        found_local.append(result)
        await update_progress()

    # Ждём Maigret и SFS
    maigret_result = await maigret_task
    sfs_result = await sfs_task

    # Объединяем результаты
    maigret_found = maigret_result.get("results", []) if "error" not in maigret_result else []
    maigret_scanned = maigret_result.get("scanned", 0)

    # Убираем дубли (сайты уже найденные в своей базе)
    local_sites = {r["site"].lower() for r in found_local}
    maigret_unique = [r for r in maigret_found if r["site"].lower() not in local_sites]

    total_found = len(found_local) + len(maigret_unique)

    # Формируем ответ
    lines = [
        f"👤 <b>Username: <code>{username}</code></b>\n"
        f"Найден на <b>{total_found}</b> сайтах "
        f"(своя база: {len(found_local)}, Maigret: {len(maigret_unique)} новых)\n"
    ]

    # StopForumSpam
    if isinstance(sfs_result, dict) and sfs_result.get("found"):
        freq = sfs_result.get("frequency", 0)
        last = sfs_result.get("lastseen", "")[:10]
        lines.append(f"🚫 <b>StopForumSpam:</b> найден в базе спамеров! ({freq} раз, последний: {last})\n")

    # Своя база — по категориям
    if found_local:
        cats = _categorize(found_local)
        lines.append("\n<b>── Собственная база ──</b>")
        for cat, items in sorted(cats.items()):
            lines.append(f"\n<b>{cat}</b>")
            for r in items:
                lines.append(f"  🟢 <a href='{r['url']}'>{r['site']}</a>")

    # Maigret — по категориям
    if maigret_unique:
        cats_m = group_by_category(maigret_unique)
        lines.append(f"\n<b>── Maigret ({maigret_scanned} сайтов) ──</b>")
        for cat, items in cats_m.items():
            lines.append(f"\n<b>{cat or 'Другое'}</b>")
            for r in items[:20]:   # не более 20 на категорию
                url = r.get("url", "")
                if url:
                    lines.append(f"  🟢 <a href='{url}'>{r['site']}</a>")
                else:
                    lines.append(f"  🟢 {r['site']}")

    if "error" in maigret_result and maigret_result["error"] != "timeout":
        lines.append(f"\n<i>⚠️ Maigret: {maigret_result['error']}</i>")

    if not total_found:
        lines.append("\n❌ Не найдено ни на одном сайте.")

    # Разбивка на части
    text = "\n".join(lines)
    parts = _split(text)
    await msg.edit_text(parts[0], parse_mode="HTML", disable_web_page_preview=True)
    for part in parts[1:]:
        await message.answer(part, parse_mode="HTML", disable_web_page_preview=True)


def _split(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts


def _categorize(results: list[dict]) -> dict[str, list[dict]]:
    category_map = {
        "Разработка": {"GitHub", "GitLab", "Bitbucket", "SourceForge", "CodePen", "Replit",
                       "JSFiddle", "Kaggle", "HackerEarth", "HackerRank", "LeetCode",
                       "Codewars", "CodinGame", "npm", "PyPI", "DockerHub", "RubyGems",
                       "crates.io", "Packagist", "Gitea", "Stack Overflow"},
        "Соцсети":    {"Twitter/X", "Instagram", "Facebook", "TikTok", "Pinterest", "Reddit",
                       "Tumblr", "VK", "OK.ru", "Mastodon", "Telegram", "LinkedIn",
                       "Snapchat", "Discord", "Clubhouse", "MeWe", "Minds", "Gab", "Parler"},
        "Видео":      {"YouTube", "Twitch", "Vimeo", "DailyMotion", "Trovo",
                       "Odysee", "Rumble", "Kick", "PeerTube"},
        "Музыка":     {"SoundCloud", "Spotify", "Last.fm", "Bandcamp", "Mixcloud",
                       "ReverbNation", "Audiomack"},
        "Игры":       {"Steam", "Chess.com", "Lichess", "Roblox", "Minecraft", "Battlenet",
                       "Kongregate", "Newgrounds", "Itch.io", "GameBanana", "Faceit"},
        "Арт / Фото": {"Flickr", "500px", "Behance", "Dribbble", "DeviantArt", "ArtStation",
                       "Unsplash", "PixelFed", "Imgur", "Wattpad"},
        "Блоги":      {"Medium", "Dev.to", "Hashnode", "Substack", "WordPress", "Ghost",
                       "Blogger", "Livejournal", "Quora", "HackerNews"},
    }
    site_to_cat = {n: cat for cat, names in category_map.items() for n in names}
    out: dict[str, list] = {}
    for r in results:
        cat = site_to_cat.get(r["site"], "Другое")
        out.setdefault(cat, []).append(r)
    return {k: v for k, v in out.items() if v}
