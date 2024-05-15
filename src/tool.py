from chimerax.core.tools import ToolInstance
from qtpy import QtWidgets as QtW
from .widgets import QCommandLineEdit

class ClixTool(ToolInstance):
    SESSION_ENDURING = False
    SESSION_SAVE = False

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)
        self.display_name = "CliX"

        from chimerax.ui import MainToolWindow
        from ._cli_utils import iter_all_commands
        self.tool_window = MainToolWindow(self)
        self._clix_widget = QCommandLineEdit(dict(iter_all_commands()), session)
        self._build_ui()

    def _build_ui(self):
        layout = QtW.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._clix_widget)

        # Set the layout as the contents of our window
        self.tool_window.ui_area.setLayout(layout)
        self.tool_window.manage('side')
        self._clix_widget.setFocus()
