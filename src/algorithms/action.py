from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy.QtWidgets import QColorDialog, QFileDialog

from ..types import FileSpec

if TYPE_CHECKING:
    from ..widgets.cli_widget import QCommandLineEdit

class Action:
    """Action to execute when the user selects the item for completion."""
    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def execute(self, widget: "QCommandLineEdit"):
        return NotImplemented

class NoAction(Action):
    def execute(self, widget: "QCommandLineEdit"):
        return None

class TypeErrorAction(Action):
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
    def history(cls) -> list[str]:
        return cls._history.copy()

class SelectFile(Action):
    _history = []

    def __init__(self, mode: str):
        self.mode = mode

    def __repr__(self):
        return f"{self.__class__.__name__}(mode={self.mode!r})"

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

class CommandPaletteAction(Action):
    def __init__(self, func, desc: str, tooltip: str):
        self.func = func
        self.desc = desc
        self.tooltip = tooltip

    def execute(self, widget: "QCommandLineEdit"):
        self.func()
        widget.setText("")

class RecentFileAction(Action):
    def __init__(self, fs: FileSpec):
        self.fs = fs
        
    def execute(self, widget: "QCommandLineEdit"):
        ctx = widget.get_context(None)
        widget.setText("")
        ctx.run_command(self.fs.open_command())
