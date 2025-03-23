from __future__ import annotations

from dataclasses import dataclass
from ..action import Action, NoAction
from ..types import Annotation

@dataclass
class CompletionState:
    text: str
    completions: list[str]
    command: str = None
    info: list[str] | None = None
    action: list[Action] | None = None
    type: str = ""
    keyword_type: type[Annotation] | Annotation | None = None
    
    def __post_init__(self):
        if self.info is None:
            self.info = [""] * len(self.completions)
        if self.action is None:
            self.action = [NoAction()] * len(self.completions)

    @classmethod
    def empty(cls) -> CompletionState:
        return cls("", [])
