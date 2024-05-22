from __future__ import annotations

from .._preference import Preference, load_preference, save_preference

from qtpy import QtWidgets as QtW, QtGui, QtCore

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
        self._area.setCurrentText(preference.area)
        layout.addRow("CliX widget area", self._area)

        self._hide_title_bar = QtW.QCheckBox("Hide title bar")
        self._hide_title_bar.setChecked(preference.hide_title_bar)
        layout.addRow(self._hide_title_bar)

        self._show_label = QtW.QCheckBox("Show \"CliX\" label on the left")
        self._show_label.setChecked(preference.show_label)
        layout.addRow(self._show_label)
        
        self._enter_completion = QtW.QCheckBox("Enable Enter key for completion")
        self._enter_completion.setChecked(preference.enter_completion)
        layout.addRow(self._enter_completion)

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
        )
        self.accept()
