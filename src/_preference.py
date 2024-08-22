import timeit
import warnings
from .user_data import CLIX_DATA_DIR, CLIX_PREFERENCE_FILE
import json
from typing import Literal
from dataclasses import dataclass, asdict, field

@dataclass
class ColorTheme:
    type: str = "#28B328"
    matched: str = "#3C6CED"
    command: str = "#AF7500"
    model: str = "#CF2424"
    keyword: str = "#808080"
    number: str = "#2CA32C"
    suggestion: str = "#B2B2B2"
    comment: str = "#A6A6B6"
    
    def __post_init__(self):
        for k, v in asdict(self).items():
            if not isinstance(v, str):
                raise ValueError(f"Invalid color value for {k}: {v!r}")

    def iteritems(self):
        return asdict(self).items()

@dataclass
class Preference:
    area: Literal["side", "bottom", "top"] = "bottom"
    hide_title_bar: bool = False
    show_label: bool = False
    enter_completion: bool = True
    auto_focus: bool = True
    color_theme: ColorTheme = field(default_factory=ColorTheme)
    
    def __post_init__(self):
        if isinstance(self.color_theme, dict):
            self.color_theme = ColorTheme(**self.color_theme)

    def as_repr(self) -> str:
        return "\n".join(f"{k} = {v!r}" for k, v in asdict(self).items())
    
    def __eq__(self, other):
        return asdict(self) == asdict(other)

_CACHED_PREFERENCE: Preference | None = None
_LAST_LOADED: float = -1

def load_preference(force: bool = True) -> Preference:
    global _CACHED_PREFERENCE, _LAST_LOADED

    now = timeit.default_timer()
    if _CACHED_PREFERENCE is not None and now - _LAST_LOADED < 0.25 and not force:
        return _CACHED_PREFERENCE
    _LAST_LOADED = now

    prepare_preference_file()
    with CLIX_PREFERENCE_FILE.open("r") as f:
        js = json.load(f)
        if not isinstance(js, dict):
            warnings.warn("Invalid preference file, using default preference")
            out = Preference()
        else:
            kwargs = {}
            for key, value in js.items():
                if key in Preference.__annotations__:
                    kwargs[key] = value
            out = Preference(**kwargs)
    _CACHED_PREFERENCE = out
    return out

def save_preference(**kwargs):
    prepare_preference_file()
    pref = load_preference()
    for k, v in kwargs.items():
        if v is not None:
            setattr(pref, k, v)
    with CLIX_PREFERENCE_FILE.open("w") as f:
        json.dump(asdict(pref), f)
    return pref

def prepare_preference_file():
    """Create directory and file if not exists."""
    if not CLIX_DATA_DIR.exists():
        CLIX_DATA_DIR.mkdir(parents=True)
    if not CLIX_PREFERENCE_FILE.exists():
        with CLIX_PREFERENCE_FILE.open("w") as f:
            json.dump(asdict(Preference()), f)
    return None
