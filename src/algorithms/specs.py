from __future__ import annotations
from typing import Iterator, TYPE_CHECKING
from contextlib import suppress
from ..types import ModelType, ChainType

class ModelSpec:
    def __init__(self, spec: str):
        ids: set[tuple[int, ...]] = set()
        for s in spec.split(","):
            if "." in s:
                s0, s1 = s.split(".", 1)
                if "-" in s1:
                    # "#1.1-3" -> (1, 1), (1, 2), (1, 3)
                    try:
                        model_id = int(s0)
                    except ValueError:
                        continue
                    start, end = s1.split("-", 1)
                    ids.update((model_id, x) for x in _safe_range(start, end))
                elif "-" in s0:
                    # not understood
                    continue
                else:
                    try:
                        ids.add((int(s0), int(s1)))
                    except ValueError:
                        continue
            else:
                if "-" in s:
                    start, end = s.split("-", 1)
                    ids.update((x,) for x in _safe_range(start, end))
                else:
                    try:
                        ids.add((int(s),))
                    except ValueError:
                        continue
        self.ids = ids

    def filter(self, models: list[ModelType]) -> list[ModelType]:
        return [m for m in models if m.id in self.ids]
    
    def contains(self, model: ModelType) -> bool:
        return model.id in self.ids

class ChainSpec:
    def __init__(self, spec: str):
        ids: set[int] = set()
        for s in spec.split(","):
            if "-" in s:
                start, end = s.split("-", 1)
                ids.update(x for x in _safe_char_range(start, end))
            else:
                try:
                    ids.add(ord(s))
                except (TypeError, ValueError):
                    continue
        self.ids = ids
    
    def filter(self, chains: list[ChainType]) -> list:
        return [c for c in chains if ord(c.chain_id) in self.ids]
    
    def contains(self, chain: ChainType) -> bool:
        return ord(chain.chain_id) in self.ids

class ResidueSpec:
    def __init__(self, spec: str):
        entries: list[tuple[int, int] | int] = []
        for s in spec.split(","):
            with suppress(ValueError):
                if "-" in s:
                    start, end = s.split("-", 1)
                    entries.append((int(start), int(end)))
                else:
                    entries.append(int(s))
        self.entries = entries
    
    def last_index(self) -> int:
        """Return the last index of the residue specification."""
        last = self.entries[-1]
        if isinstance(last, tuple):
            return last[1]
        return last


def _safe_range(start: str, end: str) -> range:
    try:
        return range(int(start), int(end) + 1)
    except ValueError:
        return range(0)

def _safe_char_range(start: str, end: str) -> Iterator[int]:
    try:
        return iter(i for i in range(ord(start), ord(end) + 1))
    except (TypeError, ValueError):
        return iter([])
