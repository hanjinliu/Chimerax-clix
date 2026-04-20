from __future__ import annotations

import time
from typing import MutableSequence, Sequence
import json
import threading
import warnings
from .user_data import CLIX_DATA_DIR, CLIX_HISTORY_FILE

# NOTE: startswith is very fast. When `entries` has 100_000 items, it takes <10 ms
# to check the prefix.
# %timeit out = [ent.startswith("ABC") for ent in entries]
# This string search is used in the history button.

# On the other hand, TrieTree is super fast for prefix searching. It takes only <1 usec
# for TrieTree with 100_000 items.

class CommandHistory(MutableSequence[str]):
    def __init__(self, codes: Sequence[str] = (), max_size: int = 20_000):
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
        if not CLIX_DATA_DIR.exists():
            CLIX_DATA_DIR.mkdir(parents=True)
        with CLIX_HISTORY_FILE.open("w") as f:
            json.dump(self._codes, f)
        return None
    
    @classmethod
    def load(cls, max_size: int = 20_000) -> CommandHistory:
        if not CLIX_HISTORY_FILE.exists():
            return CommandHistory(max_size=max_size)
        try:
            with CLIX_HISTORY_FILE.open() as f:
                codes = json.load(f)
            self = CommandHistory(codes, max_size)
        except Exception:
            self = CommandHistory(max_size=max_size)
        return self

    def append_unique(self, code: str):
        offset = max(0, len(self._codes) - 200)
        try:
            index = self._codes[offset:].index(code)
        except ValueError:
            pass
        else:
            del self._codes[offset + index]
        self.append(code)
    
    def prepend_unique(self, code: str):
        if code in self._codes:
            self._codes.remove(code)
        self.insert(0, code)

    def iter_bidirectional(
        self,
        index: int | None = None,
        last: str | None = None
    ) -> BidirectionalIterator:
        if last is None:
            codes = self._codes
        else:
            codes = self._codes + [last]
        return BidirectionalIterator(codes, index)
    

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


class TrieNode:
    """Node for TrieTree"""
    __slots__ = ('children', 'value')
    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.value: str | None = None

class TrieTree:
    def __init__(self):
        self.root = TrieNode()

    def add(self, item: str):
        node = self.root
        for char in item:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            node.value = item
    
    def set_default(self, item: str):
        node = self.root
        for char in item:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            if node.value is None:
                node.value = item

    def search(self, prefix: str) -> str | None:
        node = self.root
        for char in prefix:
            if char not in node.children:
                return None
            node = node.children[char]
        return node.value


class HistoryManager:
    """A class to manage history searching."""
    
    _instance: HistoryManager | None = None

    def __init__(self, history: CommandHistory):
        self._history = history
        self._trietree = TrieTree()
        self._trietree_initialized = False
        
        th = threading.Thread(
            target=self.prep_trie_tree, 
            args=(history,),
            daemon=True,
        )
        th.start()
        
        self._history_iter = self._history.iter_bidirectional()
        self._current_input: str = ""
        self._is_searching = False
        self._current_suggestion: str | None = None
        self.__class__._instance = self
    
    @classmethod
    def instance(cls) -> HistoryManager:
        """Return the singleton instance of the class."""
        if cls._instance is None:
            cls._instance = cls.load()
        return cls._instance

    @classmethod
    def load(cls) -> HistoryManager:
        """Load history from file and return the singleton instance."""
        history = CommandHistory.load()
        return cls(history)
    
    def add_code(self, code: str):
        """Add new code to the history."""
        self._history.append_unique(code)
        self._add_to_trietree(code)
    
    def prepend_codes(self, codes: Sequence[str]):
        """Prepend multiple codes to the history."""
        for code in reversed(codes):
            self._history.prepend_unique(code)
            self._set_default_in_trietree(code)
    
    def _add_to_trietree(self, code: str):
        self._wait_until_trietree_initialized()
        for line in code.splitlines():
            self._trietree.add(line)
    
    def _set_default_in_trietree(self, code: str):
        self._wait_until_trietree_initialized()
        for line in code.splitlines():
            self._trietree.set_default(line)
    
    def _wait_until_trietree_initialized(self):
        count = 0
        while not self._trietree_initialized:
            time.sleep(0.01)
            count += 1
            if count > 200:
                # wait for 2 seconds at most
                warnings.warn(
                    "TrieTree could not be initialized after 2 seconds.",
                    RuntimeWarning,
                    stacklevel=1,
                )
                break

    def save(self):
        """Save the history to file."""
        self._history.save()

    def init_iterator(self, last: str | None = None):
        self._history_iter = self._history.iter_bidirectional(last=last)
    
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
        """Suggest an inline completion based on the current input."""
        if current_input.strip() == "":
            return None
        if matched := self._trietree.search(current_input):
            self._current_suggestion = matched[len(current_input):]
            return self._current_suggestion
        return None

    def pop_suggestion(self) -> str | None:
        out = self._current_suggestion
        self._current_suggestion = None
        return out

    def aslist(self) -> list[str]:
        return list(self._history)

    def prep_trie_tree(self, codes: Sequence[str]):
        try:
            _trietree = TrieTree()
            for code in codes:
                for line in code.splitlines():
                    _trietree.add(line)
            self._trietree = _trietree
        finally:
            self._trietree_initialized = True
