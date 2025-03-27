from __future__ import annotations

from functools import cache
from typing import Callable
from chimerax.core.commands import run, list_selectors  # type: ignore
from chimerax.map import Volume, VolumeSurface  # type: ignore
from chimerax.core.commands import OpenFileNameArg, OpenFileNamesArg, SaveFileNameArg, OpenFolderNameArg, SaveFolderNameArg  # type: ignore
from chimerax.core.filehistory import file_history  # type: ignore
from .types import ModelType, FileSpec
from ._utils import safe_is_subclass

@cache
def chimerax_selectors() -> list[str]:
    """Iterate over all selectors available in ChimeraX.
    
    This method excludes the atoms and ion groups to avoid too many completions.
    """
    return [a for a in list_selectors() if a[0] == a[0].lower()]

def chimerax_filter_volume(models) -> list[ModelType]:
    return [m for m in models if isinstance(m, Volume)]

def chimerax_filter_surface(models) -> list[ModelType]:
    return [m for m in models if isinstance(m, VolumeSurface)]

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
