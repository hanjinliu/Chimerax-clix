from __future__ import annotations

from typing import MutableSequence, Sequence
from pathlib import Path
from platformdirs import user_data_dir
import json

DATA_DIR = Path(user_data_dir("chimerax-clix"))
HISTORY_FILE = DATA_DIR / "history.json"

class CommandHistory(MutableSequence[str]):
    def __init__(self, codes: Sequence[str] = (), max_size: int = 120):
        self._codes = list(codes)
        self._max_size = max_size
    
    def insert(self, index: int, code: str):
        self._codes.insert(index, code)
        if len(self._codes) > self._max_size:
            del self._codes[0]
        
    def __getitem__(self, index: int) -> str:
        return self._codes[index]
    
    def __setitem__(self, index: int, code: str):
        self._codes[index] = code
    
    def __delitem__(self, index: int):
        del self._codes[index]
    
    def __len__(self) -> int:
        return len(self._codes)
    
    def __iter__(self):
        return iter(self._codes)
    
    def __reversed__(self):
        return reversed(self._codes)
    
    def save(self):
        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True)
        with HISTORY_FILE.open("w") as f:
            json.dump(self._codes, f)
    
    @classmethod
    def load(cls, max_size: int = 120) -> CommandHistory:
        if not HISTORY_FILE.exists():
            return CommandHistory(max_size=max_size)
        try:
            with HISTORY_FILE.open() as f:
                codes = json.load(f)
            self = CommandHistory(codes, max_size)
        except Exception:
            self = CommandHistory(max_size=max_size)
        return self

    def append_unique(self, code: str):
        if code in self._codes:
            self._codes.remove(code)
        self.append(code)
    
    def prepend_unique(self, code: str):
        if code in self._codes:
            self._codes.remove(code)
        self.insert(0, code)
    
    def iter_bidirectional(self, index: int | None = None) -> BidirectionalIterator:
        return BidirectionalIterator(self._codes, index)
    

class BidirectionalIterator:
    def __init__(self, data: list[str], index: int | None = None):
        if index is None:
            index = len(data) - 1
        self._data = data
        self._index: int = index
    
    def next(self) -> str | None:
        cur_index = self._index
        self._index = min(self._index + 1, len(self._data) - 1)
        if cur_index < len(self._data) - 1:
            return self._data[cur_index + 1]
        return None
    
    def prev(self) -> str:
        cur_index = self._index
        self._index = max(self._index - 1, 0)
        return self._data[cur_index]

    @property
    def index(self) -> int:
        return self._index

class HistoryManager:
    """A class to manage history searching."""
    
    _instance: HistoryManager | None = None

    def __init__(self):
        self._history = CommandHistory.load()
        self._history_iter = self._history.iter_bidirectional()
        self._current_input: str = ""
        self._is_searching = False
        self._current_suggestion: str | None = None
        self.__class__._instance = self
    
    @classmethod
    def instance(cls) -> HistoryManager:
        """Return the singleton instance of the class."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def add_code(self, code: str):
        self._history.append_unique(code)
        self._history.save()
    
    def init_iterator(self):
        self._history_iter = self._history.iter_bidirectional()
    
    def look_for_prev(self, current_input: str) -> str:
        text = self._history_iter.prev()
        if not self._is_searching:
            self._current_input = current_input
        self._is_searching = True
        return text
    
    def look_for_next(self, current_input: str) -> str:
        if not self._is_searching:
            return current_input
        text = self._history_iter.next()
        if text is None and self._is_searching:
            self._is_searching = False
            text = self._current_input
        return text

    def suggest(self, current_input: str) -> str | None:
        if current_input.strip() == "":
            return None
        for code in reversed(self._history):
            for line in code.splitlines():
                if line.startswith(current_input):
                    self._current_suggestion = line[len(current_input):]
                    return self._current_suggestion
        return None

    def pop_suggestion(self) -> str | None:
        out = self._current_suggestion
        self._current_suggestion = None
        return out

    def aslist(self) -> list[str]:
        return list(self._history)
