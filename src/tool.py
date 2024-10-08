from __future__ import annotations

from chimerax.core.tools import ToolInstance
from qtpy import QtWidgets as QtW
from .widgets import QCommandLineEdit, QShowHistoryButton, QShowDialogButton
from ._preference import load_preference

class ClixTool(ToolInstance):
    SESSION_ENDURING = False
    SESSION_SAVE = False

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)
        self.display_name = "CliX"

        from chimerax.ui import MainToolWindow
        from ._cli_utils import iter_all_commands

        self._preference = load_preference()
        self.tool_window = MainToolWindow(self, hide_title_bar=self._preference.hide_title_bar)
        self._clix_widget = QCommandLineEdit(dict(iter_all_commands()), session, self._preference)
        self._history_button = QShowHistoryButton(self._clix_widget)
        self._preference_button = QShowDialogButton()
        self._build_ui()
        if self._preference.auto_focus:
            session.ui.register_for_keystrokes(self._clix_widget)

    def _build_ui(self):
        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QtW.QLabel("CliX: ")
        label.setVisible(self._preference.show_label)
        layout.addWidget(label)
        layout.addWidget(self._clix_widget)
        layout.addWidget(self._history_button)
        layout.addWidget(self._preference_button)

        # Set the layout as the contents of our window
        self.tool_window.ui_area.setLayout(layout)
        self.tool_window.manage(self._preference.area)
        self._clix_widget.setFocus()

    def delete(self):
        if self._preference.auto_focus:
            self._clix_widget._session.ui.deregister_for_keystrokes(self._clix_widget)
        return super().delete()
