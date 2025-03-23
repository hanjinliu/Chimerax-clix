from typing import TYPE_CHECKING
from qtpy.QtWidgets import QColorDialog, QFileDialog

if TYPE_CHECKING:
    from ..widgets.cli_widget import QCommandLineEdit

class Action:
    """Action to execute when the user selects the item for completion."""
    def execute(self, widget: "QCommandLineEdit"):
        return NotImplemented

class NoAction(Action):
    def execute(self, widget: "QCommandLineEdit"):
        return None

class SelectColor(Action):
    _history = []

    def execute(self, widget: "QCommandLineEdit"):
        dlg = QColorDialog(widget)
        dlg.exec()
        color = dlg.selectedColor()
        if color.isValid():
            widget.textCursor().insertText(color.name())
            self.__class__._history.append(color.name())
            if len(self.__class__._history) > 8:
                self.__class__._history.pop(0)

    @classmethod
    def history(cls):
        return cls._history.copy()

class SelectFile(Action):
    _history = []

    def __init__(self, mode: str):
        self.mode = mode

    def execute(self, widget: "QCommandLineEdit"):
        if self.mode == "r":
            path, _ = QFileDialog.getOpenFileName(widget, "Open File")
        elif self.mode == "w":
            path, _ = QFileDialog.getSaveFileName(widget, "Save File")
        elif self.mode == "d":
            path = QFileDialog.getExistingDirectory(widget, "Select Directory")
        elif self.mode == "rm":
            files, _ = QFileDialog.getOpenFileNames(widget, "Open Files")
            path = " ".join(files)
        if path:
            widget.textCursor().insertText(path)
            self.__class__._history.append(path)
            if len(self.__class__._history) > 8:
                self.__class__._history.pop(0)

    @classmethod
    def history(cls):
        return cls._history.copy()
