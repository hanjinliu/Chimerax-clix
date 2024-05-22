from chimerax.core.commands import CmdDesc, run      # Command description
from chimerax.core.commands.cli import NoArg, BoolArg, EnumOf
import json
from .user_data import COMMAND_HISTORY_PATH

def clix_show(session):
    run(session, "ui tool show clix")

clix_show_desc = CmdDesc(
    required=[], 
    optional=[],
    synopsis="show the CliX widget."
)

def clix_import_history(session, append: bool = False, include_errors: bool = False):
    from ._history import HistoryManager

    if not COMMAND_HISTORY_PATH.exists():
        raise FileNotFoundError(
            "No ChimeraX command history file found. Expected location: "
            f"{COMMAND_HISTORY_PATH.as_posix()}."
        )
    with open(COMMAND_HISTORY_PATH, "r") as f:
        history: list[tuple[str, bool]] = json.load(f)
    mgr = HistoryManager.instance()
    
    to_import: list[str] = []
    imported = set()
    for code, is_ok in history:
        if code in imported:
            continue
        if is_ok or include_errors:
            to_import.append(code)
            imported.add(code)
    if append:
        for code in to_import:
            mgr._history.append_unique(code)
    else:
        for code in to_import:
            mgr._history.prepend_unique(code)
    mgr._history.save()
    return None

clix_import_history_desc = CmdDesc(
    required=[],
    optional=[
        ("append", NoArg),
        ("include_errors", NoArg),
    ],
    synopsis="import history from the built-in CLI.",
)

def clix_preference(
    session, 
    area: str | None = None,
    hide_title_bar: bool | None = None,
    show_label: bool | None = None,
    enter_completion: bool | None = None,
    auto_focus: bool | None = None,
    show: bool = False,
):
    from ._preference import load_preference, save_preference

    old_pref = load_preference()
    new_pref = save_preference(
        area=area,
        hide_title_bar=hide_title_bar,
        show_label=show_label,
        enter_completion=enter_completion,
        auto_focus=auto_focus,
    )
    if show:
        print(new_pref.as_repr())
    if old_pref != new_pref:
        print("Please restart CliX to apply the changes.")
    return None

clix_preference_desc = CmdDesc(
    keyword=[
        ("area", EnumOf(["side", "bottom", "top"])),
        ("hide_title_bar", BoolArg),
        ("show_label", BoolArg),
        ("enter_completion", BoolArg),
        ("auto_focus", BoolArg),
        ("show", NoArg),
    ],
    synopsis="set preference of CliX.",
)
