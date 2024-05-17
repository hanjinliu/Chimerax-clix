from __future__ import annotations

import sys

if sys.platform == "win32":
    _FONT = "Consolas"
elif sys.platform == "darwin":
    _FONT = "Menlo"
else:
    _FONT = "Monospace"

class ColorPreset:
    TYPE = "#28B328"
    MATCH = "#3C6CED"
    COMMAND = "#AF7500"
    MODEL = "#CF2424"
    KEYWORD = "#808080"
    NUMBER = "#2CA32C"
    SUGGESTION = "#B2B2B2"
