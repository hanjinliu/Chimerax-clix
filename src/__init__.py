from __future__ import annotations

from chimerax.core.toolshed import BundleAPI

class CliXAPI(BundleAPI):

    api_version = 1

    @staticmethod
    def start_tool(session, bi, ti):
        from .tool import ClixTool
        from chimerax.cmd_line.tool import CommandLine
        
        # If text remains in the command line, it may be executed when CliX ends with
        # an exception.
        for _tool in session.tools.list():
            if isinstance(_tool, CommandLine):
                _tool.text.setCurrentText("")
                break
        
        return ClixTool(session, ti.name)

    @staticmethod
    def register_command(bi, ci, logger):
        from . import cmd
        if ci.name == "clix show":
            func = cmd.clix_show
            desc = cmd.clix_show_desc
        elif ci.name == "clix import history":
            func = cmd.clix_import_history
            desc = cmd.clix_import_history_desc
        elif ci.name == "clix preference":
            func = cmd.clix_preference
            desc = cmd.clix_preference_desc
        else:
            raise ValueError(f"trying to register unknown command: {ci.name}")
        
        from chimerax.core.commands import register

        register(ci.name, desc, func, logger=logger)
        

bundle_api = CliXAPI()
