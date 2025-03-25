from __future__ import annotations
from typing import Any
from dataclasses import dataclass, field

@dataclass
class WordInfo:
    """Fake word info"""
    cmd_desc: CmdDesc | None = None
    subcommands: dict[str, WordInfo] = field(default_factory=dict)

@dataclass
class CmdDesc:
    """Fake command description"""
    _required: dict[str, Any] = field(default_factory=dict)
    _optional: dict[str, Any] = field(default_factory=dict)
    _keyword: dict[str, Any] = field(default_factory=dict)
    synopsis: str | None = None
    url: str | None = None
    
    @classmethod
    def construct(
        cls,
        required: dict[str, Any] | None = None,
        optional: dict[str, Any] | None = None,
        keyword: dict[str, Any] | None = None,
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

class Annotation:
    name: str

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

_ALWAYS_DEFERRED: set[WordInfo] = set()

def resolve_cmd_desc(winfo: WordInfo) -> CmdDesc | None:
    """Resolve the command description"""
    if winfo.cmd_desc is None:
        return None
    if not hasattr(winfo.cmd_desc, "function"):
        if winfo in _ALWAYS_DEFERRED:
            return None
        winfo.cmd_desc.proxy()
    if not hasattr(winfo.cmd_desc, "function"):
        _ALWAYS_DEFERRED.add(winfo)
        return None
    return winfo.cmd_desc
