from __future__ import annotations

from pathlib import Path
from platformdirs import user_data_dir

CLIX_DATA_DIR = Path(user_data_dir("chimerax-clix"))
CLIX_HISTORY_FILE = CLIX_DATA_DIR / "history.json"
CLIX_PREFERENCE_FILE = CLIX_DATA_DIR / "preferences.json"
CLIX_LOG_PATH = CLIX_DATA_DIR / "clix.log"

CHIMERAX_DIR = Path(user_data_dir("ChimeraX", "UCSF"))
COMMAND_HISTORY_PATH = CHIMERAX_DIR / "commands"


def init_log():
    import logging

    CLIX_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLIX_LOG_PATH.touch()
    CLIX_LOG_PATH.write_text("")
    logger = logging.getLogger("chimerax.clix")
    handler = logging.FileHandler(CLIX_LOG_PATH.as_posix())
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

def read_log() -> str:
    if not CLIX_LOG_PATH.exists():
        return ""
    return CLIX_LOG_PATH.read_text()
