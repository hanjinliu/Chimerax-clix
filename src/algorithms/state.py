from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from .action import Action, NoAction
from ..types import Annotation, ModelType, WordInfo, FileSpec

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
        else:
            assert len(self.info) == len(self.completions)
        if self.action is None:
            self.action = [NoAction()] * len(self.completions)
        else:
            assert len(self.action) == len(self.completions)

    @classmethod
    def empty(cls) -> CompletionState:
        return cls("", [])

@dataclass
class Context:
    """The application context."""

    models: list[ModelType] = field(default_factory=list)
    selectors: list[str] = field(default_factory=list)
    wordinfo: WordInfo | None = None
    filter_volume: Callable[[list[ModelType]], list[ModelType]] = lambda x: x
    filter_surface: Callable[[list[ModelType]], list[ModelType]] = lambda x: x
    get_file_open_mode: Callable[[Any], str] = lambda x: "r"
    get_file_list: Callable[[], list[FileSpec]] = lambda: []
    run_command: Callable[[str], Any] = lambda x: None

    def with_models(self, models: list[ModelType]) -> Context:
        return Context(
            models=models,
            selectors=self.selectors,
            wordinfo=self.wordinfo,
            filter_volume=self.filter_volume,
            filter_surface=self.filter_surface,
            get_file_open_mode=self.get_file_open_mode,
            get_file_list=self.get_file_list,
            run_command=self.run_command,
        )
