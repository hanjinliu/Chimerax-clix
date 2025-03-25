from __future__ import annotations
from pathlib import Path
from typing import Iterable
from .state import CompletionState

def complete_path(last_word: str, current_command: str) -> CompletionState | None:
    """Return list of available paths for the given last word."""
    if completions := _complete_path_impl(last_word):
        return CompletionState(
            last_word,
            completions=completions,
            command=current_command,
            info=["(<i>path</i>)"] * len(completions),
            type="path",
        )
    return None

def _complete_path_impl(last_word: str) -> list[str] | None:
    if last_word == "":
        return None
    if last_word.endswith(("/.", "\\.")):
        # If path string ends with ".", pathlib.Path will ignore it.
        # Here, we replace it with "$" to avoid this behavior.
        _maybe_path = Path(last_word[:-1].lstrip("'").lstrip('"')).absolute() / "$"
    else:
        _maybe_path = Path(last_word.lstrip("'").lstrip('"')).absolute()
    if _maybe_path.exists():
        if _maybe_path.is_dir():
            if last_word.endswith(("/", "\\")):
                sep = ""
            else:
                sep = "\\" if "\\" in last_word else "/"
            completions = [
                sep + _p for _p in _iter_upto(p.name for p in _maybe_path.glob("*"))
            ]
            return completions
    elif _maybe_path.parent.exists() and _maybe_path != Path("/").absolute():
        _iter = _maybe_path.parent.glob("*")
        pref = _maybe_path.as_posix().rsplit("/", 1)[1]
        if pref == "$":
            pref = "."
        completions = _iter_upto(
            (p.name for p in _iter if p.name.startswith(pref)),
            include_hidden=pref.startswith(".") or pref == "$",
        )
        return completions
    return None

def _iter_upto(it: Iterable[str], n: int = 64, include_hidden: bool = False) -> list[str]:
    if include_hidden:
        return [a for _, a in zip(range(n), it)]
    else:
        return [a for _, a in zip(range(n), it) if not a.startswith(".")]
