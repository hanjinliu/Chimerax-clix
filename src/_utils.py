from __future__ import annotations

from typing import Iterable
import re

def colored(text: str, color: str) -> str:
    return f"<font color=\"{color}\">{text}</font>"

def bold_colored(text: str, color: str) -> str:
    """Return a bolded and colored HTML text."""
    return f"<b><font color={color!r}>{text}</font></b>"

def is_hex_color(text: str) -> bool:
    return (
        bool(re.match(r"^#[0-9a-fA-F]{6}$", text))
        or bool(re.match(r"^#[0-9a-fA-F]{3}$", text))
        or bool(re.match(r"^[0-9a-fA-F]{8}$", text))
    )

def rgba_to_html(rgba: Iterable[float]) -> str:
    code = "#" + "".join(hex(int(c * 255))[2:].upper().zfill(2) for c in rgba)
    if code.endswith("FF"):
        code = code[:-2]
    return code

def html_to_rgba(code: str) -> tuple[float, float, float, float]:
    if code.startswith("#"):
        code = code[1:]
    if len(code) == 3:
        code = "".join(c * 2 for c in code)
    r, g, b = int(code[:2], 16), int(code[2:4], 16), int(code[4:], 16)
    return r / 255, g / 255, b / 255, 1.0

def safe_is_subclass(obj, superclass) -> bool:
    try:
        return issubclass(obj, superclass)
    except TypeError:
        return False
