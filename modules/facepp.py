"""
Face++ (Megvii) — детекция лиц и атрибутов на фото.
Бесплатный tier: 1000 запросов/месяц.
Docs: https://console.faceplusplus.com/documents/5679127
"""
import base64
import logging
import httpx
from config import REQUEST_TIMEOUT

log = logging.getLogger(__name__)

FACEPP_API = "https://api-us.faceplusplus.com/facepp/v3"
ATTRIBUTES = "gender,age,smiling,emotion,beauty,ethnicity,facequality"


async def facepp_detect(image_bytes: bytes, api_key: str, api_secret: str) -> dict:
    """
    Детектирует лица на фото и возвращает атрибуты каждого.
    Возвращает {"faces": [...], "count": N} или {"error": "..."}
    """
    if not api_key or not api_secret:
        return {"error": "FACEPP_API_KEY/SECRET не заданы"}

    log.debug("facepp_detect: изображение %d байт", len(image_bytes))
    image_b64 = base64.b64encode(image_bytes).decode()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{FACEPP_API}/detect",
                data={
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "image_base64": image_b64,
                    "return_attributes": ATTRIBUTES,
                },
            )
            log.debug("facepp_detect: HTTP %d", r.status_code)

            if r.status_code == 401:
                return {"error": "Face++: неверный API ключ"}
            if r.status_code == 403:
                return {"error": "Face++: превышен лимит запросов"}
            if r.status_code != 200:
                return {"error": f"Face++: HTTP {r.status_code}"}

            data = r.json()
            if "error_message" in data:
                return {"error": f"Face++: {data['error_message']}"}

            faces_raw = data.get("faces", [])
            log.debug("facepp_detect: найдено %d лиц", len(faces_raw))

            faces = []
            for f in faces_raw:
                attrs = f.get("attributes", {})
                faces.append({
                    "gender": attrs.get("gender", {}).get("value", ""),
                    "age": attrs.get("age", {}).get("value"),
                    "smile": round(attrs.get("smiling", {}).get("value", 0)),
                    "beauty_male": round(attrs.get("beauty", {}).get("male_score", 0)),
                    "beauty_female": round(attrs.get("beauty", {}).get("female_score", 0)),
                    "ethnicity": attrs.get("ethnicity", {}).get("value", ""),
                    "quality": round(attrs.get("facequality", {}).get("value", 0)),
                    "emotion": _top_emotion(attrs.get("emotion", {})),
                    "rect": f.get("face_rectangle", {}),
                })

            return {"faces": faces, "count": len(faces), "image_id": data.get("image_id", "")}

    except Exception as e:
        log.error("facepp_detect: %s", e)
        return {"error": str(e)}


def _top_emotion(emotion: dict) -> str:
    if not emotion:
        return ""
    mapping = {
        "anger": "злость", "disgust": "отвращение", "fear": "страх",
        "happiness": "радость", "neutral": "нейтральность",
        "sadness": "грусть", "surprise": "удивление",
    }
    top = max(emotion, key=lambda k: emotion.get(k, 0), default="")
    return mapping.get(top, top)
