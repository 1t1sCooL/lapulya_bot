from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, PhotoSize
from modules.image_search import reverse_image_yandex
from utils.formatter import error_msg, section, list_items

router = Router()


@router.message(Command("photo"))
async def cmd_photo_help(message: Message):
    await message.answer(
        "📷 Для реверс-поиска — просто <b>отправьте фото</b> в чат.",
        parse_mode="HTML",
    )


@router.message(F.photo)
async def handle_photo(message: Message):
    msg = await message.answer("🔍 Загружаю фото в Yandex Images...")

    # Берём наибольшее разрешение
    photo: PhotoSize = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)

    result = await reverse_image_yandex(file_bytes.read(), "photo.jpg")

    if "error" in result:
        await msg.edit_text(error_msg(result["error"]), parse_mode="HTML")
        return

    text = "🖼 <b>Реверс-поиск по фото (Yandex)</b>\n"

    if result.get("results"):
        lines = []
        for r in result["results"][:8]:
            lines.append(
                f"  <a href='{r['url']}'>{r['title'][:60]}</a>\n"
                f"  <i>{r['text'][:80]}</i>\n"
            )
        text += section("Найдено совпадений", lines)
    else:
        text += "\n⚠️ Точных совпадений не найдено.\n"

    if result.get("similar_sites"):
        text += section("Сайты с похожими изображениями", [list_items(result["similar_sites"][:10])])

    if result.get("search_url"):
        text += f'\n<a href="{result["search_url"]}">🔗 Открыть в Yandex Images</a>'

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
