import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, PhotoSize
from modules.image_search import reverse_image_yandex
from modules.facepp import facepp_detect
from utils.formatter import error_msg, section, list_items
import config

router = Router()


@router.message(Command("photo"))
async def cmd_photo_help(message: Message):
    await message.answer(
        "📷 Отправь фото — реверс-поиск (Yandex) + анализ лиц (Face++).",
        parse_mode="HTML",
    )


@router.message(F.photo)
async def handle_photo(message: Message):
    msg = await message.answer("🔍 Анализирую фото...")

    photo: PhotoSize = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_io = await message.bot.download_file(file.file_path)
    image_bytes = file_io.read()

    # Параллельно: Yandex реверс-поиск + Face++ детекция
    yandex_result, face_result = await asyncio.gather(
        reverse_image_yandex(image_bytes, "photo.jpg"),
        facepp_detect(image_bytes, config.FACEPP_API_KEY, config.FACEPP_API_SECRET),
    )

    text = "🖼 <b>Анализ фото</b>\n"

    # ── Face++ ──────────────────────────────────────────────────────
    if "error" not in face_result and face_result.get("count", 0) > 0:
        faces = face_result["faces"]
        face_lines = [f"Обнаружено лиц: <b>{len(faces)}</b>\n"]
        for i, f in enumerate(faces, 1):
            gender_ru = "Мужчина" if f["gender"] == "Male" else "Женщина"
            parts = [f"#{i} {gender_ru}, ~{f['age']} лет"]
            if f.get("emotion"):
                parts.append(f"эмоция: {f['emotion']}")
            if f.get("ethnicity"):
                ethnicity_map = {"Asian": "Азиат", "White": "Европеец",
                                 "Black": "Темнокожий", "Indian": "Индиец"}
                parts.append(ethnicity_map.get(f["ethnicity"], f["ethnicity"]))
            beauty = max(f.get("beauty_male", 0), f.get("beauty_female", 0))
            if beauty:
                parts.append(f"привлекательность: {beauty}/100")
            face_lines.append("  👤 " + " | ".join(parts) + "\n")
        text += section("Face++ — Анализ лиц", face_lines)
    elif "error" in face_result and "не заданы" not in face_result["error"]:
        text += section("Face++", [f"⚠️ {face_result['error']}\n"])
    elif face_result.get("count") == 0:
        text += section("Face++", ["😶 Лица не обнаружены\n"])

    # ── Yandex реверс-поиск ─────────────────────────────────────────
    if "error" not in yandex_result:
        if yandex_result.get("results"):
            lines = []
            for r in yandex_result["results"][:6]:
                lines.append(
                    f"  <a href='{r['url']}'>{r['title'][:60]}</a>\n"
                    f"  <i>{r['text'][:80]}</i>\n"
                )
            text += section("Yandex — совпадения", lines)
        else:
            text += section("Yandex", ["⚠️ Точных совпадений не найдено\n"])

        if yandex_result.get("similar_sites"):
            text += section("Похожие сайты", [list_items(yandex_result["similar_sites"][:8])])

        if yandex_result.get("search_url"):
            text += f'\n<a href="{yandex_result["search_url"]}">🔗 Открыть в Yandex Images</a>'
    else:
        text += section("Yandex", [f"⚠️ {yandex_result['error']}\n"])

    if len(text) > 4000:
        text = text[:3980] + "\n<i>… обрезано</i>"

    await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
