from __future__ import annotations

from .._preference import Preference, load_preference, save_preference

from qtpy import QtWidgets as QtW

class QShowDialogButton(QtW.QPushButton):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        # set standard icon
        self.setText("⚙")
        self.setFixedWidth(30)
        self.setToolTip("Show preference dialog")
        self.clicked.connect(self._on_clicked)
    
    def _on_clicked(self):
        dialog = QPreferenceDialog(self.parent())
        dialog.exec_()
    
class QPreferenceDialog(QtW.QDialog):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._init_ui(load_preference())

    def _init_ui(self, preference: Preference):
        self.setWindowTitle("CliX Preference")

        layout = QtW.QFormLayout()
        self.setLayout(layout)

        self._area = QtW.QComboBox()
        self._area.addItems(["top", "side", "bottom"])
        self._area.setToolTip("The area where the CliX widget will be placed")
        self._area.setCurrentText(preference.area)
        layout.addRow("CliX widget area", self._area)

        self._hide_title_bar = QtW.QCheckBox("Hide title bar")
        self._hide_title_bar.setToolTip(
            "This will hide the title bar of the CliX widget, just like the built-in "
            "command line."
        )
        self._hide_title_bar.setChecked(preference.hide_title_bar)
        layout.addRow(self._hide_title_bar)

        self._show_label = QtW.QCheckBox("Show \"CliX\" label on the left")
        self._show_label.setToolTip(
            "This will show the \"CliX\" label on the left of the CliX widget command "
            "line."
        )
        self._show_label.setChecked(preference.show_label)
        layout.addRow(self._show_label)
        
        self._enter_completion = QtW.QCheckBox("Enable Enter key for completion")
        self._enter_completion.setToolTip(
            "Pressing Enter key will select the completion suggestion, instead of "
            "executing the command."
        )
        self._enter_completion.setChecked(preference.enter_completion)
        layout.addRow(self._enter_completion)

        self._auto_focus = QtW.QCheckBox("Focus on CliX widget when typing")
        self._auto_focus.setToolTip(
            "Automatically focus on the CliX widget when typing. This option is useful "
            "when you have to go back and forth between the CliX widget and the main "
            "window."
        )
        self._auto_focus.setChecked(preference.auto_focus)
        layout.addRow(self._auto_focus)

        buttons = QtW.QDialogButtonBox()
        buttons.setStandardButtons(
            QtW.QDialogButtonBox.StandardButton.Cancel 
            | QtW.QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_ok(self):
        save_preference(
            area=self._area.currentText(),
            hide_title_bar=self._hide_title_bar.isChecked(),
            show_label=self._show_label.isChecked(),
            enter_completion=self._enter_completion.isChecked(),
            auto_focus=self._auto_focus.isChecked(),
        )
        self.accept()
