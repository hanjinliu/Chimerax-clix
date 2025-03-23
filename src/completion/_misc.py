from __future__ import annotations

from pathlib import Path
import itertools
from typing import Any, Iterable, Iterator
from chimerax.core.commands import list_selectors  # type: ignore
from chimerax.core.commands import OpenFileNameArg, OpenFileNamesArg, SaveFileNameArg, OpenFolderNameArg, SaveFolderNameArg  # type: ignore

from .state import CompletionState
from .action import NoAction, SelectColor, SelectFile
from ..types import resolve_cmd_desc, WordInfo, CmdDesc
from ..algorithms import filepath
from .._utils import colored

def complete_path(last_word: str, current_command: str) -> CompletionState | None:
    """Return list of available paths for the given last word."""
    if completions := filepath.complete_path(last_word):
        return CompletionState(
            last_word,
            completions=completions,
            command=current_command,
            info=["(<i>path</i>)"] * len(completions),
            type="path",
        )
    return None

def complete_keyword_name_or_value(
    winfo: WordInfo, args: list[str], last_word: str, current_command: str, text: str
) -> CompletionState | None:
    """Get completion state for given command arguments
    
    Parameters
    ----------
    winfo : WordInfo
        Info for the current command
    args : list[str]
        List of arguments (not including the currently typed word)
    last_word : str
        The currently typed word
    current_command : str
        The current command string
    text : str
        The entire command string
    """
    cmd_desc = resolve_cmd_desc(winfo)
    if cmd_desc is None:
        return CompletionState(text, [], current_command)
    
    last_pref = args[-1]
    keyword_just_typed = last_pref in cmd_desc._keyword
    if keyword_just_typed:
        last_annot = cmd_desc._keyword[last_pref]
        state = complete_keyword_value(last_annot, last_word, current_command)
        if state is not None:
            return state
    else:
        it = itertools.chain(cmd_desc._required.values(), cmd_desc._optional.values())
        next_arg = None
        for _ in range(len(args) - len(current_command.split(" ")) + 1):
            next_arg = next(it, None)

        if next_arg:
            if state := complete_keyword_value(next_arg, last_word, current_command):
                return state
            elif is_spec(next_arg):
                map_table = str.maketrans({c: " " for c in "&|~"})
                last_word = last_word.translate(map_table).split(" ")[-1]
                selectors = [s for s in iter_selectors() if s.startswith(last_word)]
                if selectors:
                    return CompletionState(
                        last_word,
                        completions=selectors,
                        command=current_command,
                        info=["(<i>selector</i>)"] * len(selectors),
                        type="selector",
                    )

    if keyword_just_typed and not is_noarg(cmd_desc._keyword[last_pref]):
        return None
    
    # Show keyword list. To make the keywords ordered, we first show the optional
    # arguments.
    return completion_state_for_word(cmd_desc, last_word, current_command)

def complete_keyword_value(
    last_annot, 
    last_word: str,
    current_command: str,
) -> CompletionState | None:
    """Get completion for keyword value of specific types."""
    if is_enumof(last_annot):
        values = to_list_of_str(last_annot.values, startswith=last_word)
        return _from_values(values, last_word, current_command, "enum", last_annot)
    elif is_dynamic_enum(last_annot):
        values = to_list_of_str(last_annot.value_func(), startswith=last_word)
        if len(values) == 1 and last_word == values[0]:
            values = []
        return _from_values(values, last_word, current_command, "enum", last_annot)
    elif is_boolean(last_annot):
        values = ["true", "false"]
        return _from_values(values, last_word, current_command, "boolean", last_annot)
        
    elif is_onoff(last_annot):
        values = ["on", "off"]
        return _from_values(values, last_word, current_command, "on/off", last_annot)

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
            info=["(<i>enum</i>)"] * len(values),
            type="keyword-value",
            keyword_type=last_annot,
        )

    elif is_color(last_annot):
        color_hist = SelectColor.history()
        return CompletionState(
            text=last_word,
            completions=[""] + color_hist,
            command=current_command,
            info=["<i>Select a color ...</i>"] + [colored("▉", c) for c in color_hist],
            type="keyword-value",
            action=[SelectColor()] + [NoAction()] * len(color_hist),
            keyword_type=last_annot,
        )

    elif is_file_path(last_annot):
        paths = [Path.home().as_posix()] + SelectFile.history()
        if last_word and (states := complete_path(last_word, current_command)):
            paths.extend(states.completions)
        if safe_is_subclass(last_annot, OpenFileNameArg):
            mode = "r"
        elif safe_is_subclass(last_annot, OpenFileNamesArg):
            mode = "rm"
        elif safe_is_subclass(last_annot, SaveFileNameArg):
            mode = "w"
        elif safe_is_subclass(last_annot, OpenFolderNameArg):
            mode = "d"
        else:
            mode = "r"  # never happens
        
        return CompletionState(
            text=last_word,
            completions=[""] + paths,
            command=current_command,
            info=["<i>Browse ...</i>"] + ["(<i>path</i>)"] * len(paths),
            type="keyword-value",
            action=[SelectFile(mode=mode)] + [NoAction()] * len(paths),
            keyword_type=last_annot,
        )

    elif is_or(last_annot):
        # concatenate all the completions
        completions = []
        info = []
        action = []
        for each in last_annot.annotations:
            if state := complete_keyword_value(each, last_word, current_command):
                completions.extend(state.completions)
                info.extend(state.info)
                action.extend(state.action)
        if completions:
            return CompletionState(
                text=last_word,
                completions=completions,
                command=current_command,
                info=info,
                action=action,
                type="keyword-value",
                keyword_type=last_annot,
            )
    return None

def _from_values(
    values: list[str],
    last_word: str,
    current_command: str,
    info_str: str,
    last_annot,
) -> CompletionState:
    if len(values) == 1 and last_word == values[0]:
        values = []
    return CompletionState(
        text=last_word,
        completions=values,
        command=current_command,
        info=[f"(<i>{info_str}</i>)"] * len(values),
        type="keyword-value",
        keyword_type=last_annot,
    )

def completion_state_for_word(
    cmd_desc: CmdDesc,
    last_word: str,
    current_command: str,
) -> CompletionState | None:
    comp_list: list[str] = []
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
            info=["(<i>keyword</i>)"] * len(comp_list),
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

def is_onoff(annotation) -> bool:
    return getattr(annotation, "name", "") == "on or off"

def is_noarg(annotation) -> bool:
    return type(annotation).__name__ == "NoArg"

def is_spec(annotation) -> bool:
    return getattr(annotation, "name", "") == "an objects specifier"

def is_or(annotation) -> bool:
    return type(annotation).__name__ == "Or"

def is_color(annotation) -> bool:
    return getattr(annotation, "name", "") == "a color"

def is_file_path(annotation) -> bool:
    return hasattr(annotation, "check_existence")

def iter_selectors() -> Iterator[str]:
    """Iterate over all selectors available in ChimeraX.
    
    This method excludes the atoms and ion groups to avoid too many completions.
    """
    return (a for a in list_selectors() if a[0] == a[0].lower())

def to_list_of_str(it: Iterable[Any], startswith: str = "") -> list[str]:
    out: list[str] = []
    for a in it:
        if str(a).startswith(startswith):
            out.append(str(a))
    return out

def safe_is_subclass(obj, superclass) -> bool:
    try:
        return issubclass(obj, superclass)
    except TypeError:
        return False
