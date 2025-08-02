from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui

class QSelectResiduesDialog(QtW.QDialog):
    def __init__(self, characters: str, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Select residues ...")
        self.setModal(True)
        self._characters = characters

    def exec_select(self) -> list[tuple[int, int]]:
        # TODO: implement this
        return []