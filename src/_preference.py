from .user_data import CLIX_DATA_DIR, CLIX_PREFERENCE_FILE
import json
from typing import Literal
from dataclasses import dataclass, asdict

@dataclass
class Preference:
    area: Literal["side", "bottom", "top"] = "side"

def load_preference() -> Preference:
    if not CLIX_PREFERENCE_FILE.exists():
        return Preference()
    with CLIX_PREFERENCE_FILE.open("r") as f:
        return Preference(**json.load(f))

def save_preference(**kwargs):
    if not CLIX_DATA_DIR.exists():
        CLIX_DATA_DIR.mkdir(parents=True)
    pref = load_preference()
    for k, v in kwargs.items():
        setattr(pref, k, v)
    with CLIX_PREFERENCE_FILE.open("w") as f:
        json.dump(asdict(pref), f)
