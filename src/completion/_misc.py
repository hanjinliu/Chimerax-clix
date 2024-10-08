from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Iterator
from .state import CompletionState
from ..types import resolve_cmd_desc, WordInfo

def _iter_upto(it: Iterable[str], n: int = 64, include_hidden: bool = False) -> list[str]:
    if include_hidden:
        return [a for _, a in zip(range(n), it)]
    else:
        return [a for _, a in zip(range(n), it) if not a.startswith(".")]

def complete_path(last_word: str, current_command: str) -> CompletionState | None:
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
            completions = [sep + _p for _p in _iter_upto(p.name for p in _maybe_path.glob("*"))]
            return CompletionState(
                "",
                completions=completions,
                command=current_command,
                info=["<i>path</i>"] * len(completions),
                type="path",
            )
    elif _maybe_path.parent.exists() and _maybe_path != Path("/").absolute():
        _iter = _maybe_path.parent.glob("*")
        pref = _maybe_path.as_posix().rsplit("/", 1)[1]
        if pref == "$":
            pref = "."
        completions = _iter_upto(
            (p.name for p in _iter if p.name.startswith(pref)),
            include_hidden=pref.startswith(".") or pref == "$",
        )
        return CompletionState(
            pref,
            completions=completions,
            command=current_command,
            info=["<i>path</i>"] * len(completions),
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
            if len(values) == 1 and last_word == values[0]:
                values = []
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
            if len(values) == 1 and last_word == values[0]:
                values = []
            return CompletionState(
                text=last_word,
                completions=values,
                command=current_command,
                info=["<i>enum</i>"] * len(values),
                type="keyword-value",
                keyword_type=cmd_desc._keyword[last_pref],
            )
        elif is_boolean(last_annot):
            values = ["true", "false"]
            if len(values) == 1 and last_word == values[0]:
                values = []
            return CompletionState(
                text=last_word,
                completions=values,
                command=current_command,
                info=["<i>boolean</i>"] * len(values),
                type="keyword-value",
                keyword_type=cmd_desc._keyword[last_pref],
            )
        elif is_listof_enumof(last_annot):
            last_word = last_word.split(",")[-1]
            values = to_list_of_str(
                last_annot.annotation.values,
                startswith=last_word
            )
            if len(values) == 1 and last_word == values[0]:
                values = []
            valid_values = [v for v in values if v.startswith(last_word)]
            return CompletionState(
                text=last_word,
                completions=valid_values,
                command=current_command,
                info=["<i>enum</i>"] * len(values),
                type="keyword-value",
                keyword_type=cmd_desc._keyword[last_pref],
            )
    else:
        if (
            is_spec(next(iter(cmd_desc._required.values()), None))
            or is_spec(next(iter(cmd_desc._optional.values()), None))
        ):
            map_table = str.maketrans({c: " " for c in "&|~"})
            last_word = last_word.translate(map_table).split(" ")[-1]
            selectors = [s for s in iter_selectors() if s.startswith(last_word)]
            return CompletionState(
                last_word,
                completions=selectors,
                command=current_command,
                info=["<i>selector</i>"] * len(selectors),
                type="selector",
            )

    if keyword_just_typed and not is_noarg(cmd_desc._keyword[last_pref]):
        return None
    
    # Show keyword list. To make the keywords ordered, we first show the optional
    # arguments.
    keywords = cmd_desc._keyword.copy()
    for _k in cmd_desc._optional.keys():
        if _k not in keywords:
            continue
        if _k.startswith(last_word):
            comp_list.append(_k)
            keywords.pop(_k)
    for _k in keywords.keys():
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

def is_listof_enumof(annotation) -> bool:
    return type(annotation).__name__ == "ListOf" and is_enumof(annotation.annotation)

def is_boolean(annotation) -> bool:
    return getattr(annotation, "name", "") == "true or false"

def is_noarg(annotation) -> bool:
    return type(annotation).__name__ == "NoArg"

def is_spec(annotation) -> bool:
    return getattr(annotation, "name", "") == "an objects specifier"

def iter_selectors() -> Iterator[str]:
    # Iterate over all selectors available in ChimeraX (except for the atoms and ion
    # groups to avoid too many completions).
    
    from chimerax.core.commands import list_selectors  # type: ignore
    
    return (a for a in list_selectors() if a[0] == a[0].lower())

def to_list_of_str(it: Iterable[Any], startswith: str = "") -> list[str]:
    out: list[str] = []
    for a in it:
        if str(a).startswith(startswith):
            out.append(str(a))
    return out
