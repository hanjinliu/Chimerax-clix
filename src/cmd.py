from chimerax.core.commands import CmdDesc, run      # Command description
from chimerax.core.commands.cli import NoArg, EnumOf
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

def clix_preference(session, area: str = "side"):
    from ._preference import save_preference

    save_preference(area=area)
    return None

clix_preference_desc = CmdDesc(
    keyword=[("area", EnumOf(["side", "bottom", "top"]))],
    synopsis="set preference of CliX.",
)
