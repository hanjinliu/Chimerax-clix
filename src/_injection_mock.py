from __future__ import annotations

from typing import Callable, ParamSpec, TypeVar
from ._types import ModelType, FileSpec

_P = ParamSpec("_P")
_R = TypeVar("_R")

def chimerax_selectors() -> list[str]:
    return []

def chimerax_filter_volume(models) -> list[ModelType]:
    return []

def chimerax_filter_surface(models) -> list[ModelType]:
    return []

def chimerax_filter_atom(models) -> list[ModelType]:
    return []

def chimerax_filter_pseudo_bond(models) -> list[ModelType]:
    return []

def chimerax_filter_bond(models) -> list[ModelType]:
    return []

def chimerax_file_history(session) -> Callable[[], list[FileSpec]]:
    return lambda: []

def chimerax_get_mode(last_annot: type) -> str:
    return "r"

def chimerax_run(session):
    return lambda line: None

def chimerax_builtin_colors() -> dict[str, str]:
    return {}

def chimerax_get_selector_description(selector: str, session) -> str:
    return ""
