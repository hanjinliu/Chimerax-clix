from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable
from .action import Action, NoAction
from ..types import Annotation, ModelType, WordInfo

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

@dataclass
class Context:
    models: list[ModelType] = field(default_factory=list)
    selectors: list[str] = field(default_factory=list)
    wordinfo: WordInfo | None = None
    filter_volume: Callable[[list[ModelType]], list[ModelType]] = lambda x: x
    filter_surface: Callable[[list[ModelType]], list[ModelType]] = lambda x: x
    get_file_open_mode: Callable[[Any], str] = lambda x: "r"

    def with_models(self, models: list[ModelType]) -> Context:
        new = asdict(self)
        new["models"] = models
        return Context(**new)
