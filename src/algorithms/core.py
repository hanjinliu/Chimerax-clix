from __future__ import annotations

from pathlib import Path
import itertools
from typing import Any, Iterable

from .state import CompletionState
from ..action import NoAction, SelectColor, SelectFile
from .action import NoAction, TypeErrorAction, SelectColor, SelectFile
from .filepath import complete_path
from .state import CompletionState, Context
from .model import complete_model, complete_chain, complete_residue, complete_atom
from ..types import resolve_cmd_desc
from .._utils import colored, is_hex_color

# For types, see https://github.com/RBVI/ChimeraX/tree/develop/src/bundles/core/src/commands

def complete_keyword_name_or_value(
    args: list[str],
    last_word: str, 
    current_command: str,
    text: str,
    context: Context,
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
    cmd_desc = resolve_cmd_desc(context.wordinfo, current_command)
    if cmd_desc is None:
        return CompletionState(text, [], current_command)

    # last_pref is used to determine the last keyword argument
    if len(args) > 0:
        last_pref = args[-1]
    else:
        last_pref = ""
    
    keyword_just_typed = last_pref in cmd_desc._keyword
    not_enough_args = len(cmd_desc._required) > len(args) - int(keyword_just_typed)
    if keyword_just_typed:
        # if not all the required arguments are given, complete the keyword value
        if not_enough_args:
            return CompletionState(
                text=text,
                completions=[""],
                command=current_command,
                info=[colored("Not enough arguments", "red")],
                action=[TypeErrorAction()],
                type="keyword-value",
            )
        last_annot = cmd_desc._keyword[last_pref]
        if state := complete_keyword_value(last_annot, last_word, current_command, context):
            return state
    else:
        it = itertools.chain(cmd_desc._required.values(), cmd_desc._optional.values())
        next_arg = None
        for _ in range(len(args) + 1):
            next_arg = next(it, None)
        if next_arg:
            if state := complete_keyword_value(next_arg, last_word, current_command, context):
                return state

    if keyword_just_typed and not is_noarg(cmd_desc._keyword[last_pref]):
        return None
    
    # Show keyword list. To make the keywords ordered, we first show the optional
    # arguments.
    if not_enough_args:
        return None
    return list_keywords(last_word, current_command, context)

def complete_keyword_value(
    last_annot, 
    last_word: str,
    current_command: str,
    context: Context
) -> CompletionState | None:
    """Get completion for keyword value of specific types."""

    if is_noarg(last_annot):
        return list_keywords(last_word, current_command, context)
    elif is_enumof(last_annot):
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
        valid_values = [v for v in values if v.startswith(last_word)]
        if len(valid_values) == 1 and last_word == valid_values[0]:
            valid_values = []
        elif len(valid_values) == 0:
            return None
        return CompletionState(
            text=last_word,
            completions=valid_values,
            command=current_command,
            info=["(<i>enum</i>)"] * len(valid_values),
            type="keyword-value",
            keyword_type=last_annot,
        )

    elif is_color(last_annot):
        color_hist = SelectColor.history()
        completions = []
        info = []
        if last_word == "":
            completions = [""] + color_hist
            info = ["<i>Select a color ...</i>"] + [colored("▉", c) for c in color_hist]
            action = [SelectColor()] + [NoAction()] * len(color_hist)
        elif last_word.startswith("#"):
            if len(last_word) < 7:
                for hex in color_hist:
                    if hex.startswith(last_word.lower()):
                        completions.append(hex)
                        info.append(colored("▉", hex))
            elif is_hex_color(last_word):
                completions.append(last_word)
                info.append(colored("▉", last_word))
            else:
                pass
            action = [NoAction()] * len(completions)
        else:
            for name, hex in context.colors.items():
                if name.startswith(last_word):
                    completions.append(name)
                    info.append(colored("▉", hex))
            action = [NoAction()] * len(completions)
        return CompletionState(
            text=last_word,
            completions=completions,
            command=current_command,
            info=info,
            type="keyword-value",
            action=action,
            keyword_type=last_annot,
        )

    elif is_file_path(last_annot):
        if last_word and (states := complete_path(last_word, current_command)):
            paths = states.completions
            info = ["(<i>path</i>)"] * len(paths)
            action = [NoAction()] * len(paths)
        else:
            # empty
            mode = context.get_file_open_mode(last_annot)
            paths = [""] + [Path.home().as_posix()] + SelectFile.history()
            npaths = len(paths) - 1
            info=["<i>Browse ...</i>"] + ["(<i>path</i>)"] * npaths
            action=[SelectFile(mode=mode)] + [NoAction()] * npaths
        
        return CompletionState(
            text=last_word,
            completions=paths,
            command=current_command,
            info=info,
            type="keyword-value,path",
            action=action,
            keyword_type=last_annot,
        )

    elif is_axis(last_annot):
        return CompletionState(
            text=last_word,
            completions=["x", "y", "z", "-x", "-y", "-z"],
            command=current_command,
            info=["(<i>axis</i>)"] * 6,
            type="keyword-value",
            keyword_type=last_annot,
        )
    
    elif is_target_arg(last_annot):
        return CompletionState(
            text=last_word,
            completions=["a", "c", "r", "s", "b", "p", "f", "m"],
            command=current_command,
            info=[
                colored(f"<i>= {word}</i>", "gray")
                for word 
                in ["atoms", "cartoon", "cartoon", "surfaces", "bonds", "pseudobonds", "(filled) rings", "models"]
            ],
            type="keyword-value",
            keyword_type=last_annot,
        )
    
    elif is_colormap(last_annot):
        return CompletionState(
            text=last_word,
            completions=["rainbow", "grayscale", "red-white-blue", "blue-white-red", "cyan-white-maroon"],
            command=current_command,
            info=["(<i>colormap</i>)"] * 5,
            type="keyword-value",
            keyword_type=last_annot,
        )

    elif is_value_type(last_annot):
        return CompletionState(
            text=last_word,
            completions=["int8", "uint8", "int16", "uint16", "int32", "uint32", "float32", "float64"],
            command=current_command,
            info=["(<i>value type</i>)"] * 8,
            type="keyword-value",
            keyword_type=last_annot,
        )

    elif is_or(last_annot):
        # concatenate all the completions
        completions = []
        info = []
        action = []
        for each in last_annot.annotations:
            if state := complete_keyword_value(each, last_word, current_command, context):
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
    
    if is_model_like(last_annot):
        if is_density_map(last_annot):
            filt = context.filter_volume
        elif is_surface(last_annot):
            filt = context.filter_surface
        else:
            filt = lambda x: x
        if len(last_word) == 0 or last_word.startswith("#"):
            return complete_model(context, last_word, current_command, model_filter=filt)
        if last_word.startswith("/"):
            return complete_chain(context, last_word, current_command, model_filter=filt)
        if last_word.startswith(":"):
            return complete_residue(context, last_word, current_command, model_filter=filt)
        if last_word.startswith("@"):
            return complete_atom(context, last_word, current_command)
        if is_spec(last_annot):
            map_table = str.maketrans({c: " " for c in "&|~"})
            last_word = last_word.translate(map_table).split(" ")[-1]
            selectors = [s for s in context.selectors if s.startswith(last_word)]
            if selectors:
                return CompletionState(
                    last_word,
                    completions=selectors,
                    command=current_command,
                    info=["(<i>selector</i>)"] * len(selectors),
                    type="selector",
                )
    return None

def _from_values(
    values: list[str],
    last_word: str,
    current_command: str,
    info_str: str,
    last_annot,
) -> CompletionState | None:
    if len(values) == 1 and last_word == values[0]:
        # single match, no need to show
        values = []
    elif len(values) == 0:
        # no match. Return None to allow other completions
        return None
    return CompletionState(
        text=last_word,
        completions=values,
        command=current_command,
        info=[f"(<i>{info_str}</i>)"] * len(values),
        type="keyword-value",
        keyword_type=last_annot,
    )

def list_keywords(
    last_word: str,
    current_command: str,
    context: Context,
) -> CompletionState | None:
    comp_list: list[str] = []
    cmd_desc = resolve_cmd_desc(context.wordinfo, current_command)
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

def is_model(annotation) -> bool:
    return getattr(annotation, "name", "") in (
        "a model specifier", 
        "a models specifier",
        "a model id",  # TODO: is this correct?
    )

def is_surface(annotation) -> bool:
    return getattr(annotation, "name", "") in (
        "a surface specifier",
        "a surfaces specifier",
    )

def is_density_map(annotation) -> bool:
    return getattr(annotation, "name", "") in (
        "a density map specifier",
        "a density maps specifier",
    )

def is_value_type(annotation) -> bool:
    return getattr(annotation, "name", "") == "numeric value type"

def is_model_like(last_annot) -> bool:
    return (
        is_model(last_annot)
        or is_surface(last_annot) 
        or is_density_map(last_annot)
        or is_spec(last_annot)
    )

def is_spec(annotation) -> bool:
    return getattr(annotation, "name", "") == "an objects specifier"

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
    return getattr(annotation, "__name__", "") == "NoArg"

def is_or(annotation) -> bool:
    return type(annotation).__name__ == "Or"

def is_color(annotation) -> bool:
    return getattr(annotation, "name", "") == "a color"

def is_file_path(annotation) -> bool:
    return hasattr(annotation, "check_existence")

def is_axis(annotation) -> bool:
    return getattr(annotation, "name", "") == "an axis vector"

def to_list_of_str(it: Iterable[Any], startswith: str = "") -> list[str]:
    out: list[str] = []
    for a in it:
        if str(a).startswith(startswith):
            out.append(str(a))
    return out

def is_target_arg(annotation) -> bool:
    return getattr(annotation, "__name__", "") == "TargetArg"

def is_colormap(annotation) -> bool:
    return getattr(annotation, "name", "") == "a colormap"
