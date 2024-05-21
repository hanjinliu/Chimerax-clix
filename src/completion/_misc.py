from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable
from .state import CompletionState
from ..types import resolve_cmd_desc, WordInfo

def _iter_upto(it: Iterable[str], n: int = 64, include_hidden: bool = False) -> list[str]:
    if include_hidden:
        return [a for _, a in zip(range(n), it)]
    else:
        return [a for _, a in zip(range(n), it) if not a.startswith(".")]

def complete_path(last_word: str, current_command: str) -> CompletionState | None:
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
            return CompletionState(
                "",
                [sep + _p for _p in _iter_upto(p.name for p in _maybe_path.glob("*"))], 
                current_command,
                type="path",
            )
    elif _maybe_path.parent.exists() and _maybe_path != Path("/").absolute():
        _iter = _maybe_path.parent.glob("*")
        pref = _maybe_path.as_posix().rsplit("/", 1)[1]
        if pref == "$":
            pref = "."
        return CompletionState(
            pref,
            _iter_upto(
                (p.name for p in _iter if p.name.startswith(pref)),
                include_hidden=pref.startswith(".") or pref == "$",
            ),
            current_command,
            type="path",
        )
    return None


def complete_keyword_name_or_value(
    winfo: WordInfo, pref: list[str], last_word: str, current_command: str, text: str
) -> CompletionState | None:
    comp_list: list[str] = []
    cmd_desc = resolve_cmd_desc(winfo)
    if cmd_desc is None:
        return CompletionState(text, [], current_command)
    
    last_pref = pref[-1]
    keyword_just_typed = last_pref in cmd_desc._keyword
    if keyword_just_typed:
        last_annot = cmd_desc._keyword[last_pref]
        if is_enumof(last_annot):
            values = to_list_of_str(last_annot.values, startswith=last_word)
            return CompletionState(
                text=last_word,
                completions=values,
                command=current_command,
                info=["<i>enum</i>"] * len(values),
                type="keyword-value",
                keyword_type=cmd_desc._keyword[last_pref],
            )
        elif is_dynamic_enum(last_annot):
            values = to_list_of_str(last_annot.value_func(), startswith=last_word)
            return CompletionState(
                text=last_word,
                completions=values,
                command=current_command,
                info=["<i>enum</i>"] * len(values),
                type="keyword-value",
                keyword_type=cmd_desc._keyword[last_pref],
            )
        elif is_boolean(last_annot):
            return CompletionState(
                text=last_word,
                completions=["true", "false"],
                command=current_command,
                info=["<i>boolean</i>"] * 2,
                type="keyword-value",
                keyword_type=cmd_desc._keyword[last_pref],
            )
    
    if keyword_just_typed and not is_noarg(cmd_desc._keyword[last_pref]):
        return None
    for _k in cmd_desc._keyword.keys():
        if _k.startswith(last_word):
            comp_list.append(_k)
    if len(comp_list) > 0:
        return CompletionState(
            last_word, 
            completions=comp_list, 
            command=current_command,
            info=["<i>keyword</i>"] * len(comp_list),
            type="keyword",
        )
    return None

def is_enumof(annotation) -> bool:
    return type(annotation).__name__ == "EnumOf"

def is_dynamic_enum(annotation) -> bool:
    return type(annotation).__name__ == "DynamicEnum"

def is_boolean(annotation) -> bool:
    return getattr(annotation, "name", "") == "true or false"

def is_noarg(annotation) -> bool:
    return type(annotation).__name__ == "NoArg"

def to_list_of_str(it: Iterable[Any], startswith: str = "") -> list[str]:
    out: list[str] = []
    for a in it:
        if str(a).startswith(startswith):
            out.append(str(a))
    return out
