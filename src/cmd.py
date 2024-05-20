from chimerax.core.commands import CmdDesc, run      # Command description

def clix_show(session):
    run(session, "ui tool show clix")

clix_show_desc = CmdDesc(required=[], optional=[])

def clix_replace(session):
    code = 'ui tool hide "command line interface"\nui tool show clix'
