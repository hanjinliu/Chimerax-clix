from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Callable

class Annotation:
    name: str

@dataclass
class WordInfo:
    """Fake word info"""
    cmd_desc: CmdDesc | None = None
    subcommands: dict[str, WordInfo] = field(default_factory=dict)

@dataclass
class CmdDesc:
    """Fake command description"""
    _required: dict[str, Annotation] = field(default_factory=dict)
    _optional: dict[str, Annotation] = field(default_factory=dict)
    _keyword: dict[str, Annotation] = field(default_factory=dict)
    synopsis: str | None = None
    url: str | None = None
    
    @classmethod
    def construct(
        cls,
        required: dict[str, Annotation] | None = None,
        optional: dict[str, Annotation] | None = None,
        keyword: dict[str, Annotation] | None = None,
        synopsis: str | None = None,
        url: str | None = None,
    ) -> CmdDesc:
        return cls(
            _required=required or {},
            _optional=optional or {},
            _keyword=keyword or {},
            synopsis=synopsis,
            url=url,
        )

@dataclass
class FileSpec:
    """Fake file specification"""
    path: str
    image: str
    open_command: Callable[[], str]

@dataclass
class ModelType:
    """Fake model type"""
    id: tuple[int, ...]
    name: str
    chains: list[ChainType] = field(default_factory=list)
    nonstandard_residue_names: set[str] = field(default_factory=set)

@dataclass
class ChainType:
    """Fake chain type"""
    chain_id: str
    description: str | None = None
    residues: list[ResidueType | None] = field(default_factory=list)
    characters: str = ""
    numbering_start: int = 1

@dataclass
class ResidueType:
    """Fake residue type"""
    name: str
    description: str | None = None
    number: int = field(default=0)
    one_letter_code: str = "X"
    is_strand: bool = False
    is_helix: bool = False

_ALWAYS_DEFERRED = {"kvfinder"}

def resolve_cmd_desc(winfo: WordInfo, command_name: str) -> CmdDesc | None:
    """Resolve the command description"""
    if winfo.cmd_desc is None:
        return None
    if not hasattr(winfo.cmd_desc, "function"):
        if command_name in _ALWAYS_DEFERRED:
            return None
        winfo.cmd_desc.proxy()
    if not hasattr(winfo.cmd_desc, "function"):
        _ALWAYS_DEFERRED.add(command_name)
        return None
    return winfo.cmd_desc

class Mode(Enum):
    CLI = "cli"
    PALETTE = "palette"
    RECENT = "recent"
