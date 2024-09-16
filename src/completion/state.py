from __future__ import annotations

from dataclasses import dataclass
from ..types import Annotation

@dataclass
class CompletionState:
    text: str
    completions: list[str]
    command: str | None = None
    info: list[str] | None = None
    type: str = ""
    keyword_type: type[Annotation] | Annotation | None = None
    
    @classmethod
    def empty(cls) -> CompletionState:
        return cls("", [])
