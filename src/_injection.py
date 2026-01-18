from __future__ import annotations

from typing import Callable, TYPE_CHECKING
from chimerax.core.commands import (  # type: ignore
    run,
    list_selectors,
    get_selector_description,
    OpenFileNameArg,
    OpenFileNamesArg,
    SaveFileNameArg,
    OpenFolderNameArg,
    SaveFolderNameArg
)
from chimerax.map import Volume, VolumeSurface  # type: ignore
from chimerax.core.colors import BuiltinColors, BuiltinColormaps  # type: ignore
from chimerax.core.filehistory import file_history  # type: ignore
from chimerax.atomic import StructureData, Pseudobond, Bond  # type: ignore
from ._types import ModelType, FileSpec
from ._utils import safe_is_subclass

if TYPE_CHECKING:
    from typing import ParamSpec, TypeVar

    _P = ParamSpec("_P")
    _R = TypeVar("_R")

class cached_function(Callable["_P", "_R"]):
    """Custom cached function decorator that supports clearing the cache."""
    def __init__(self, func: "Callable[_P, _R]"):
        self._func = func
        self._cache = None

    def __call__(self, *args: "_P.args", **kwargs: "_P.kwargs") -> "_R":
        if self._cache is None:
            self._cache = self._func(*args, **kwargs)
        return self._cache
    
    def clear_cache(self):
        """Clear the cache."""
        self._cache = None

def chimerax_model_list(session) -> list[ModelType]:
    """Get the list of all models in the current session."""
    return session.models.list()

@cached_function
def chimerax_selectors() -> list[str]:
    """Iterate over all selectors available in ChimeraX.
    
    This method excludes the atoms and ion groups to avoid too many completions.
    """
    return [a for a in list_selectors()]

def chimerax_filter_volume(models) -> list[ModelType]:
    return [m for m in models if isinstance(m, Volume)]

def chimerax_filter_surface(models) -> list[ModelType]:
    return [m for m in models if isinstance(m, VolumeSurface)]

def chimerax_filter_atom(models) -> list[ModelType]:
    return [m for m in models if isinstance(m, StructureData)]

def chimerax_filter_pseudo_bond(models) -> list[ModelType]:
    return [m for m in models if isinstance(m, Pseudobond)]

def chimerax_filter_bond(models) -> list[ModelType]:
    return [m for m in models if isinstance(m, Bond)]

def chimerax_file_history(session) -> Callable[[], list[FileSpec]]:
    def _get_hist():
        hist = file_history(session)
        return [fs for fs in hist.files]
    return _get_hist

def chimerax_get_mode(last_annot: type) -> str:
    if safe_is_subclass(last_annot, OpenFileNameArg):
        mode = "r"
    elif safe_is_subclass(last_annot, OpenFileNamesArg):
        mode = "rm"
    elif safe_is_subclass(last_annot, SaveFileNameArg) or safe_is_subclass(last_annot, SaveFolderNameArg):
        mode = "w"
    elif safe_is_subclass(last_annot, OpenFolderNameArg):
        mode = "d"
    else:
        mode = "r"  # never happens
    return mode

def chimerax_run(session):
    def _run(line):
        return run(session, line)
    return _run

@cached_function
def chimerax_builtin_colors() -> dict[str, str]:
    out: dict[str, str] = {}
    for name, color in BuiltinColors.items():
        if " " not in name:
            out[name] = color.hex()
    return out

def chimerax_get_selector_description(selector: str, session) -> str:
    """Get the description of a selector."""
    return get_selector_description(selector, session)
