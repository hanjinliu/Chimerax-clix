from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy.QtWidgets import QColorDialog, QFileDialog

from .._utils import colored
from ..types import FileSpec, ResidueType
from ..consts import ONE_LETTER_TO_THREE_LETTER

if TYPE_CHECKING:
    from ..widgets.cli_widget import QCommandLineEdit

class Action:
    """Action to execute when the user selects the item for completion."""
    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def execute(self, widget: "QCommandLineEdit"):
        return NotImplemented
    
    def info(self) -> str:
        """Return a string that describes the action."""
        return ""

class NoAction(Action):
    def execute(self, widget: "QCommandLineEdit"):
        # usually results in the fallback completion action
        return None

class TypeErrorAction(Action):
    def info(self) -> str:
        return colored("Not enough arguments", "red")

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

class ResidueAction(Action):
    def __init__(self, res: ResidueType):
        self.res = res
    
    def info(self) -> str:
        """Return a string that describes the residue action."""
        char = self.res.one_letter_code
        if self.res.is_strand:
            secondary = " β"
        elif self.res.is_helix:
            secondary = " α"
        else:
            secondary = ""
        return f"<b>{self.res.number}: {self.res.name.title()} ({char}){secondary}</b>"
    
    def execute(self, widget: "QCommandLineEdit"):
        text = widget.text()
        cursor = widget.textCursor()
        pos_start = cursor.position() - 1
        if pos_start < 0:
            return
        while True:
            if text[pos_start] in (",", ":", "-"):
                break
            if text[pos_start] in ("\n", " ", "\t") or pos_start <= 0:
                return  # should not reach here, just return
            pos_start -= 1
        cursor.clearSelection()
        cursor.setPosition(pos_start + 1, mode=cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(str(self.res.number))
        widget._close_popups()

class MissingResidueAction(Action):
    def __init__(self, index: int, char: str):
        self.index = index
        self.char = char

    def info(self) -> str:
        return f"<s>{self.index}: {ONE_LETTER_TO_THREE_LETTER.get(self.char, '---')} ({self.char})</s>"

    def execute(self, widget: "QCommandLineEdit"):
        return
