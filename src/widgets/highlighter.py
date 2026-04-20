from __future__ import annotations

from typing import TYPE_CHECKING
import logging
import timeit
from qtpy import QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt
from ..algorithms import CompletionState
from .consts import _FONT
from .._types import resolve_cmd_desc, Mode, WordInfo
from .._preference import load_preference


LOGGER = logging.getLogger(__name__)


class QCommandLineEditBase(QtW.QTextEdit):
    def __init__(self, commands: dict[str, WordInfo]):
        super().__init__()
        self.setFont(QtGui.QFont(_FONT))
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._commands = commands
        self._mode = Mode.CLI
        self._current_completion_state = CompletionState.empty()
        
        self._highlighter = QCommandHighlighter(self)
        self.set_height_for_block_counts()

    @property
    def completion_state(self) -> CompletionState:
        return self._current_completion_state

    def set_height_for_block_counts(self):
        nblocks = min(max(self.document().blockCount(), 1), 6)
        self.setFixedHeight((self.fontMetrics().height() + 2) * nblocks + 6)
        self.verticalScrollBar().setVisible(nblocks > 2)

class QCommandHighlighter(QtGui.QSyntaxHighlighter):
    """Syntax highlighter for QCommandLineEdit."""
    def __init__(self, parent: QCommandLineEditBase):
        super().__init__(parent.document())
        self._command_strings = set()
        for cmd in parent._commands.keys():
            self._command_strings.add(cmd)
            if " " in cmd:
                self._command_strings.add(cmd.split(" ", 1)[0])
        self._parent = parent
    
    def highlightBlock(self, text: str):
        t0 = timeit.default_timer()
        self._highlight_block_impl(text)
        t1 = timeit.default_timer()
        dt = (t1 - t0) * 1000
        dt_slow_ms = 50
        if dt > dt_slow_ms:
            LOGGER.warning("Bad performance in highlightBlock: %.1f ms for text %r", dt, text)

    def _highlight_block_impl(self, text: str):
        if text.strip() == "":
            return
        _color_theme = load_preference(force=False).color_theme
        if self._parent._mode is not Mode.CLI:
            self.setFormat(0, 1, QtGui.QTextCharFormat())
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(QtGui.QColor(_color_theme.comment))
            self.setFormat(1, len(text), QtGui.QTextCharFormat())
            return None
        if text.startswith("#"):
            # comment
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(QtGui.QColor(_color_theme.comment))
            self.setFormat(0, len(text), fmt)
            return None
        if text.endswith("?"):
            return self.highlightBlock(text[:-1])
        cur_command: list[str] = []
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

    def _is_keyword(self, word: str) -> bool:
        cmd = self._parent.completion_state.command
        if cmd is None:
            return False
        winfo = self._parent._commands[cmd]
        cmd_desc = resolve_cmd_desc(winfo, cmd)
        if cmd_desc is None:
            return False
        return word in cmd_desc._keyword.keys()
    
    def _is_real_number(self, word: str) -> bool:
        try:
            float(word)
            return True
        except Exception:
            return False
