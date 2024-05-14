from __future__ import annotations
from typing import Any

class WordInfo:
    cmd_desc: CmdDesc | None
    subcommands: dict[str, WordInfo]

class CmdDesc:
    _required: dict[str, Any]
    _optional: dict[str, Any]
    _keyword: dict[str, Any]
    synopsis: str | None

def resolve_cmd_desc(winfo: WordInfo) -> CmdDesc | None:
    """Resolve the command description"""
    if winfo.cmd_desc is None:
        return None
    if not hasattr(winfo.cmd_desc, "function"):
        winfo.cmd_desc.proxy()
    if not hasattr(winfo.cmd_desc, "function"):
        return None
    return winfo.cmd_desc
