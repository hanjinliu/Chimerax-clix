from __future__ import annotations
from typing import Iterator
from .types import WordInfo

def get_registry() -> WordInfo:
    """Get the ChimeraX command registry"""
    from chimerax.core.commands.cli import _command_info  # type: ignore
    
    return _command_info.commands

def iter_commands(
    cmds: dict[str, WordInfo], 
    parent: str = "",
) -> Iterator[tuple[list[str], WordInfo]]:
    for key, value in cmds.items():
        if parent:
            cmd = f"{parent} {key}"
        else:
            cmd = key
        if value.cmd_desc is not None:
            yield cmd, value
        if value.subcommands:
            yield from iter_commands(value.subcommands, cmd)


def iter_all_commands():
    """Iterate over all commands in the registry"""
    cmds = get_registry()
    yield from iter_commands(cmds.subcommands)
