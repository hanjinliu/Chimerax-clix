from pathlib import Path
from platformdirs import user_data_dir

CLIX_DATA_DIR = Path(user_data_dir("chimerax-clix"))
CLIX_HISTORY_FILE = CLIX_DATA_DIR / "history.json"
CLIX_PREFERENCE_FILE = CLIX_DATA_DIR / "preferences.json"

CHIMERAX_DIR = Path(user_data_dir("ChimeraX", "UCSF"))
COMMAND_HISTORY_PATH = CHIMERAX_DIR / "commands"
