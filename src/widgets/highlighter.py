from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy import QtGui
from ..types import resolve_cmd_desc
from .._preference import load_preference

if TYPE_CHECKING:
    from .cli_widget import QCommandLineEdit

class QCommandHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent: QCommandLineEdit):
        super().__init__(parent.document())
        self._command_strings = set()
        for cmd in parent._commands.keys():
            self._command_strings.add(cmd)
            if " " in cmd:
                self._command_strings.add(cmd.split(" ", 1)[0])
        self._parent = parent
    
    def highlightBlock(self, text: str):
        _color_theme = load_preference(force=False).color_theme
        if text.startswith("#"):
            # comment
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(QtGui.QColor(_color_theme.comment))
            self.setFormat(0, len(text), fmt)
            return None
        if text.endswith("?"):
            return self.highlightBlock(text[:-1])
        cur_command = []
        cur_start = 0
        cur_stop = 0
        for word in text.split(" "):
            if word != "":
                cur_command.append(word)
            next_stop = cur_stop + len(word)
            if " ".join(cur_command) in self._command_strings:
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(QtGui.QColor(_color_theme.command))
                fmt.setFontWeight(QtGui.QFont.Weight.Bold)
                self.setFormat(cur_start, next_stop, fmt)
            elif word.startswith(("#", "/", ":", "@")):
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(QtGui.QColor(_color_theme.model))
                self.setFormat(cur_start, next_stop, fmt)
            elif self._is_keyword(word):
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(QtGui.QColor(_color_theme.keyword))
                self.setFormat(cur_start, next_stop, fmt)
            elif self._is_real_number(word):
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(QtGui.QColor(_color_theme.number))
                self.setFormat(cur_start, next_stop, fmt)
            else:
                self.setFormat(cur_start, next_stop, QtGui.QTextCharFormat())
            cur_start = next_stop + 1
            cur_stop += len(word) + 1

        return None

    def _is_keyword(self, word: str) -> bool:
        cmd = self._parent._current_completion_state.command
        if cmd is None:
            return False
        winfo = self._parent._commands[cmd]
        cmd_desc = resolve_cmd_desc(winfo)
        if cmd_desc is None:
            return False
        return word in cmd_desc._keyword.keys()
    
    def _is_real_number(self, word: str) -> bool:
        try:
            float(word)
            return True
        except Exception:
            return False
