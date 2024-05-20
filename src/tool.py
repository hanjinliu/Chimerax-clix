from chimerax.core.tools import ToolInstance
from qtpy import QtWidgets as QtW
from .widgets import QCommandLineEdit, QShowHistoryButton
from ._preference import load_preference

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
        self._history_button = QShowHistoryButton(self._clix_widget)
        self._build_ui()

    def _build_ui(self):
        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._clix_widget)
        layout.addWidget(self._history_button)

        # Set the layout as the contents of our window
        self.tool_window.ui_area.setLayout(layout)
        self.tool_window.manage(load_preference().area)
        self._clix_widget.setFocus()
