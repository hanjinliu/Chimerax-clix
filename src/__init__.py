from __future__ import annotations

from chimerax.core.toolshed import BundleAPI

class _MyAPI(BundleAPI):

    api_version = 1

    @staticmethod
    def start_tool(session, bi, ti):
        from .tool import ClixTool
        return ClixTool(session, ti.name)

    @staticmethod
    def register_command(bi, ci, logger):
        from . import cmd
        if not ci.name == "clix":
            return
        
        from chimerax.core.commands import register
        register("clix show", cmd.clix_show_desc, cmd.clix_show)

bundle_api = _MyAPI()
