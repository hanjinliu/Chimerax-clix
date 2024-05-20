from pathlib import Path
from platformdirs import user_data_dir

CHIMERAX_DIR = Path(user_data_dir("ChimeraX", "UCSF"))

COMMAND_HISTORY_PATH = CHIMERAX_DIR / "commands"
