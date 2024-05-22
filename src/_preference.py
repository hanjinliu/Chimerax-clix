from .user_data import CLIX_DATA_DIR, CLIX_PREFERENCE_FILE
import json
from typing import Literal
from dataclasses import dataclass, asdict

@dataclass
class Preference:
    area: Literal["side", "bottom", "top"] = "side"
    hide_title_bar: bool = False
    show_label: bool = False
    enter_completion: bool = True
    auto_focus: bool = True

    def as_repr(self) -> str:
        return "\n".join(f"{k} = {v!r}" for k, v in asdict(self).items())
    
    def __eq__(self, other):
        return asdict(self) == asdict(other)

def load_preference() -> Preference:
    if not CLIX_PREFERENCE_FILE.exists():
        return Preference()
    with CLIX_PREFERENCE_FILE.open("r") as f:
        js = json.load(f)
        kwargs = {}
        for key, value in js.items():
            if key in Preference.__annotations__:
                kwargs[key] = value
        return Preference(**kwargs)

def save_preference(**kwargs):
    if not CLIX_DATA_DIR.exists():
        CLIX_DATA_DIR.mkdir(parents=True)
    pref = load_preference()
    for k, v in kwargs.items():
        if v is not None:
            setattr(pref, k, v)
    with CLIX_PREFERENCE_FILE.open("w") as f:
        json.dump(asdict(pref), f)
    return pref
