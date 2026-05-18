from typing import Any


def kv(label: str, value: Any, bold: bool = True) -> str:
    if value is None or value == "" or value == []:
        return ""
    label_part = f"<b>{label}:</b>" if bold else f"{label}:"
    return f"{label_part} <code>{value}</code>\n"


def section(title: str, lines: list[str]) -> str:
    body = "".join(l for l in lines if l)
    if not body:
        return ""
    return f"\n<b>── {title} ──</b>\n{body}"


def list_items(items: list[str], max_items: int = 20) -> str:
    shown = items[:max_items]
    result = "\n".join(f"  • <code>{i}</code>" for i in shown)
    if len(items) > max_items:
        result += f"\n  <i>...и ещё {len(items) - max_items}</i>"
    return result + "\n" if result else ""


def error_msg(text: str) -> str:
    return f"❌ <b>Ошибка:</b> {text}"


def not_found(what: str) -> str:
    return f"🔍 Ничего не найдено для <code>{what}</code>"
