from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from ..types import WordInfo, resolve_cmd_desc
from .._history import HistoryManager
from ..completion import (
    CompletionState, complete_path, complete_keyword_name_or_value, complete_model, 
    complete_chain, complete_residue, complete_atom
)
from chimerax.core.commands import run  # type: ignore
from .consts import _FONT, TOOLTIP_FOR_AMINO_ACID
from .popups import QCompletionPopup, QTooltipPopup
from .highlighter import QCommandHighlighter
from .._utils import colored
from .._preference import Preference

class QSuggestionLabel(QtW.QLabel):
    """Label widget for inline suggestion."""
    
    clicked = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.setCursor(Qt.CursorShape.IBeamCursor)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.clicked.emit()
        return super().mousePressEvent(event)

class QCommandLineEdit(QtW.QTextEdit):
    def __init__(self, commands: dict[str, WordInfo], session, preference: Preference):
        super().__init__()
        self.setFont(QtGui.QFont(_FONT))
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self._on_text_changed)
        self._commands = commands
        self._current_completion_state = CompletionState.empty()
        self._list_widget = self._create_list_widget()
        self._tooltip_widget = self._create_tooltip_widget()
        self._inline_suggestion_widget = self._create_suggestion_widget()
        self._session = session
        self._highlighter = QCommandHighlighter(self)
        self.set_height_for_block_counts()
        self._dont_need_inline_suggestion = False
        self._preference = preference

    def _update_completion_state(self, allow_auto: bool = False) -> bool:
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine, QtGui.QTextCursor.MoveMode.KeepAnchor)
        self._current_completion_state = self._get_completion_list(cursor.selectedText())
        if len(self._current_completion_state.completions) == 0:
            return False
        if len(self._current_completion_state.completions) == 1 and allow_auto:
            self._complete_with(self._current_completion_state.completions[0])
        return True

    def text(self) -> str:
        text = self.toPlainText()
        return text.replace("\u2029", "\n")

    def run_command(self):
        code = self.text().rstrip()
        if code == "":
            return None
        if code.endswith("?"):
            self._open_help_viewer(code[:-1].strip())
            return None
        try:
            for line in code.split("\n"):
                if line.strip() == "":
                    continue
                run(self._session, line)
        except Exception:
            HistoryManager.instance().init_iterator(last=code)
            raise
        else:
            if code:
                HistoryManager.instance().add_code(code)
            HistoryManager.instance().init_iterator()
        finally:
            self.setText("")
            self._current_completion_state = CompletionState.empty()

    def _open_help_viewer(self, code: str):
        from chimerax.help_viewer import show_url  # type: ignore
            
        if command := self._commands.get(code, None):
            if out := resolve_cmd_desc(command):
                if out.url:
                    show_url(self._session, out.url)
            else:
                raise ValueError(f"Command {code!r} does not have CmdDesc.")
        else:
            raise ValueError(f"Command {code!r} not found.")
        return None

    def _adjust_tooltip_for_list(self, idx: int):
        item_rect = self._list_widget.visualItemRect(self._list_widget.item(idx))
        pos = self._list_widget.mapToGlobal(item_rect.topRight())
        if _is_too_bottom(pos.y() + self._tooltip_widget.height()):
            pos = self._list_widget.mapToGlobal(
                item_rect.bottomRight() - QtCore.QPoint(0, self._tooltip_widget.height())
            )
        pos.setX(pos.x() + 10)
        self._tooltip_widget.move(pos)

    def _list_selection_changed(self, idx: int, text: str):
        if not self._list_widget.isVisible():
            return
        if self._current_completion_state.type in ("residue", "model,residue"):
            # set residue name
            tooltip = TOOLTIP_FOR_AMINO_ACID.get(text.split(":")[-1], "")
            if tooltip:
                self._tooltip_widget.setText(tooltip)
                # adjust the height of the tooltip
                metrics = QtGui.QFontMetrics(self._tooltip_widget.font())
                height = min(280, metrics.height() * (tooltip.count("\n") + 1) + 6)
                self._tooltip_widget.setFixedHeight(height)
                # move the tooltip
                self._try_show_tooltip_widget()
        elif self._current_completion_state.type in ("keyword", "selector"):
            pass
        elif winfo := self._commands.get(text, None):
            self._adjust_tooltip_for_list(idx)
            self._tooltip_widget.setWordInfo(winfo, text)
            self._try_show_tooltip_widget()
        
    def _create_list_widget(self):
        list_widget = QCompletionPopup()
        list_widget.setParent(self, Qt.WindowType.ToolTip)
        list_widget.setFont(self.font())
        list_widget.changed.connect(self._list_selection_changed)
        return list_widget
    
    def _create_tooltip_widget(self):
        tooltip_widget = QTooltipPopup()
        tooltip_widget.setParent(self, Qt.WindowType.ToolTip)
        tooltip_widget.setFont(self.font())
        return tooltip_widget

    def _create_suggestion_widget(self):
        suggestion_widget = QSuggestionLabel()
        suggestion_widget.setFont(self.font())
        suggestion_widget.setParent(self, Qt.WindowType.ToolTip)
        try:
            bg_color = self.viewport().palette().color(QtGui.QPalette.ColorRole.Base)
            html_color = bg_color.name()
        except Exception:
            html_color = "#ffffff"
        suggestion_widget.setStyleSheet(
            "QSuggestionLabel { background-color: " + html_color + "; }"
        )
        suggestion_widget.hide()
        @suggestion_widget.clicked.connect
        def _inline_clicked():
            self.setFocus()
            self._close_tooltip_and_list()
        return suggestion_widget
    
    def _current_and_matched_commands(self, text: str) -> tuple[str, list[str]]:
        matched_commands: list[str] = []
        current_command: str | None = None
        text_lstrip = text.lstrip()
        text_strip = text.strip()
        for command_name in self._commands.keys():
            if command_name.startswith(text_lstrip):
                # if `text` is "toolshed", add
                #   toolshed list
                #   toolshed install ...
                # to `matched_commands`
                matched_commands.append(command_name)
            elif text_strip == command_name or text_strip.startswith(command_name.rstrip() + " "):
                current_command = command_name
        return current_command, matched_commands

    def _get_completion_list(self, text: str) -> CompletionState:
        if text == "" or text.startswith("#"):
            return CompletionState(text, [], type="empty-text")

        # command completion
        current_command, matched_commands = self._current_and_matched_commands(text)
        if len(matched_commands) > 0:
            if len(matched_commands) == 1 and matched_commands[0] == text.strip():
                # not need to show the completion list
                pass
            elif " " not in text:
                # if `matched_commands` is
                #   toolshed list
                #   toolshed install
                # then `all_commands` is
                #   toolshed
                #   toolshed list
                #   toolshed install
                all_commands: dict[str, None] = {}  # ordered set
                for cmd in matched_commands:
                    all_commands[cmd.split(" ")[0]] = None
                for cmd in matched_commands:
                    all_commands[cmd] = None
                matched_commands = list(all_commands.keys())
            return CompletionState(text, matched_commands, current_command, type="command")
    
        # attribute completion
        *pref, last_word = text.rsplit(" ")
        if pref == []:
            return CompletionState(text, [], current_command)
        if last_word.startswith("#"):
            return complete_model(self._session.models.list(), last_word, current_command)
        if last_word.startswith("/"):
            return complete_chain(self._session.models.list(), last_word, current_command)
        if last_word.startswith(":"):
            return complete_residue(self._session.models.list(), last_word, current_command)
        if last_word.startswith("@"):
            return complete_atom(self._session, last_word, current_command)

        cmd = current_command or self._current_completion_state.command
        if winfo := self._commands.get(cmd, None):
            # command keyword name/value completion
            if state := complete_keyword_name_or_value(winfo, pref, last_word, current_command, text):
                return state

        # path completion
        if state := complete_path(last_word, current_command):
            return state

        return CompletionState(text, [], current_command)
   
    def _on_text_changed(self):
        self._inline_suggestion_widget.hide()

        # look for the completion
        self._update_completion_state(False)
        self._try_show_list_widget()
        if self._list_widget.isVisible():
            self._list_widget.setCurrentRow(0)

        # if needed, show/hide the tooltip widget
        if self._current_completion_state.command is None:
            if self._tooltip_widget.isVisible():
                self._tooltip_widget.hide()
        elif self._current_completion_state.type in ("residue", "model,residue"):
            self._try_show_tooltip_widget()    
        else:
            name = self._current_completion_state.command
            cmd = self._commands[name]
            self._tooltip_widget.setWordInfo(cmd, name)
            self._try_show_tooltip_widget()
        
        # resize the widget
        self.set_height_for_block_counts()
        
        if self._list_widget.count() > 0:
            self._list_widget.set_row(0)
        
        # one-line suggestion
        if not self._dont_need_inline_suggestion:
            this_line = self.textCursor().block().text()
            if this_line.startswith("#"):
                # comment line does not need suggestion
                return None
            if suggested := HistoryManager.instance().suggest(this_line):
                self._show_inline_suggestion(suggested)
        return None
    
    def _show_inline_suggestion(self, suggested: str):
        if suggested.startswith(" "):
            # the first spaces are not visible when using HTML
            _stripped = suggested.lstrip()
            suggested = "&nbsp;" * (len(suggested) - len(_stripped)) + _stripped
        self._inline_suggestion_widget.setText(
            colored(suggested, self._preference.color_theme.suggestion)
        )
        cursor_rect = self.cursorRect()
        label_height = QtGui.QFontMetrics(self.font()).height()
        cursor_height = cursor_rect.height()
        dh = (cursor_height - label_height) // 2
        tr = cursor_rect.topRight()
        cursor_point = QtCore.QPoint(tr.x() + 1, tr.y() + dh)
        self._inline_suggestion_widget.move(self.mapToGlobal(cursor_point))
        self._inline_suggestion_widget.show()
        return None

    def _apply_inline_suggestion(self):
        cursor = self.textCursor()
        if not cursor.atEnd():
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
        if sug := HistoryManager.instance().pop_suggestion():
            self.insertPlainText(sug)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
            self.setTextCursor(cursor)
        self._inline_suggestion_widget.hide()
        self._close_popups()
        return True

    def _try_show_list_widget(self):
        self._update_completion_state(allow_auto=False)
        items = self._current_completion_state.completions
        
        # if nothing to show, do not show the list
        if len(items) == 0:
            self._list_widget.hide()
            return
        
        # if the next character exists and is not a space, do not show the list
        _cursor = self.textCursor()
        if not _cursor.atEnd():
            _cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.Right,
                QtGui.QTextCursor.MoveMode.KeepAnchor
            )
            if not _cursor.selectedText().isspace():
                self._list_widget.hide()
                return
        
        self._list_widget.add_items_with_highlight(self._current_completion_state)
        self._list_widget.resizeForContents()
        if not self._list_widget.isVisible():
            self._list_widget.show()
        _height = self._list_widget.height()
        pos = self.mapToGlobal(self.cursorRect().bottomLeft())
        if _is_too_bottom(_height + pos.y()):
            pos = self.mapToGlobal(self.cursorRect().topLeft()) - QtCore.QPoint(0, _height)
        self._list_widget.move(pos)
        return None
    
    def _try_show_tooltip_widget(self):
        tooltip = self._tooltip_widget.toPlainText()
        if (
            not self._tooltip_widget.isVisible()
            and tooltip != ""
            and self._current_completion_state.type != "path"
        ):
            # show tooltip because there's something to show
            self._tooltip_widget.show()
            self.setFocus()
        elif tooltip == "":
            self._tooltip_widget.hide()
        
        if self._tooltip_widget.isVisible():
            if self._list_widget.isVisible():
                # show next to the cursor
                self._adjust_tooltip_for_list(self._list_widget.currentRow())
            else:
                # show beside the completion list
                _height = self._tooltip_widget.height()
                pos = self.mapToGlobal(self.cursorRect().bottomRight())
                if _is_too_bottom(pos.y() + _height):
                    pos = self.mapToGlobal(self.cursorRect().topRight()) - QtCore.QPoint(0, _height)
                self._tooltip_widget.move(pos)
        return None

    def _complete_with(self, comp: str):
        _n = len(self._current_completion_state.text)
        self.insertPlainText(comp[_n:])
        self._update_completion_state(False)
        self._close_popups()
        return None
    
    def forwarded_keystroke(self, event: QtGui.QKeyEvent):
        """Forward the key event from the main window."""
        if self._session.ui.key_intercepted(event.key()):
            return None
        if not self.isVisible():
            return None
        if (
            event.key() not in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Meta, Qt.Key.Key_Alt)
            and not event.matches(QtGui.QKeySequence.StandardKey.Undo)
            and not event.matches(QtGui.QKeySequence.StandardKey.Redo)
        ):
            self.setFocus()
        self.event(event)
        return None
    
    def _keypress_event(self, event: QtGui.QKeyEvent):
        self._dont_need_inline_suggestion = False
        done = False
        if event.key() == Qt.Key.Key_Tab:
            done = self._event_tab(event)
        elif event.key() == Qt.Key.Key_Down:
            done = self._event_down(event)
        elif event.key() == Qt.Key.Key_PageDown:
            done = self._event_page_down(event)
        elif event.key() == Qt.Key.Key_Up:
            done = self._event_up(event)
        elif event.key() == Qt.Key.Key_PageUp:
            done = self._event_page_up(event)
        elif event.key() == Qt.Key.Key_Right:
            done = self._event_right(event)
        elif event.key() == Qt.Key.Key_End:
            done = self._event_end(event)
        elif event.key() == Qt.Key.Key_Left:
            self._close_tooltip_and_list()
        elif event.key() == Qt.Key.Key_Home:
            self._close_tooltip_and_list()
        elif event.key() == Qt.Key.Key_Return:
            done = self._event_return(event)
        elif event.key() == Qt.Key.Key_Escape:
            done = self._event_escape(event)
        elif event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self._dont_need_inline_suggestion = True
        elif event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._dont_need_inline_suggestion = True
        elif event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            done = self._event_paste(event)
        return done

    def _event_tab(self, event: QtGui.QKeyEvent):
        if self._list_widget.isVisible():
            self._complete_with_current_item()
        elif not self._update_completion_state(True):
            pass
        else:
            self._try_show_list_widget()
        return True
    
    def _event_paste(self, event: QtGui.QKeyEvent):
        self._current_completion_state = CompletionState.empty()
        # if html is pasted, converted it to a plain text
        clip = QtW.QApplication.clipboard()
        text = clip.text()
        self.insertPlainText(text)
        return True
    
    def _event_down(self, event: QtGui.QKeyEvent):
        self._dont_need_inline_suggestion = True
        if self._list_widget.isVisible():
            if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                self._list_widget.goto_next()
            elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._list_widget.goto_last()
            else:
                return super().event(event)
            return True
        cursor = self.textCursor()
        if cursor.blockNumber() == self.document().blockCount() - 1:
            mgr = HistoryManager.instance()
            self.setText(mgr.look_for_next(self.text()))
            self.setTextCursor(cursor)
            if not mgr._is_searching:
                self._current_completion_state = CompletionState.empty()
            return True
        self._close_tooltip_and_list()
        return False
    
    def _event_page_down(self, event: QtGui.QKeyEvent):
        self._inline_suggestion_widget.hide()
        self._dont_need_inline_suggestion = True
        if self._list_widget.isVisible():
            self._list_widget.goto_next_page()
            return True
        self._close_tooltip_and_list()
    
    def _event_up(self, event: QtGui.QKeyEvent):
        self._inline_suggestion_widget.hide()
        self._dont_need_inline_suggestion = True
        if self._list_widget.isVisible():
            if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                self._list_widget.goto_previous()
            elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._list_widget.goto_first()
            else:
                return super().event(event)
            return True
        cursor = self.textCursor()
        if cursor.blockNumber() == 0:
            self.setText(HistoryManager.instance().look_for_prev(self.text()))
            self.setTextCursor(cursor)
            return True
        self._close_tooltip_and_list()
        return False

    def _event_page_up(self, event: QtGui.QKeyEvent):
        self._inline_suggestion_widget.hide()
        self._dont_need_inline_suggestion = True
        if self._list_widget.isVisible():
            self._list_widget.goto_previous_page()
            return True
        self._close_tooltip_and_list()
        return False

    def _event_right(self, event: QtGui.QKeyEvent):
        cursor = self.textCursor()
        if cursor.atBlockEnd() and self._inline_suggestion_widget.isVisible():
            self._apply_inline_suggestion()
            return True
        self._close_tooltip_and_list()
        return False
    
    def _event_end(self, event: QtGui.QKeyEvent):
        if self._inline_suggestion_widget.isVisible():
            self._apply_inline_suggestion()
            return True
        self._close_tooltip_and_list()
        return False

    def _event_return(self, event: QtGui.QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if self._list_widget.isVisible() and self._preference.enter_completion:
                self._complete_with_current_item()
            else:
                self.run_command()
            return True
        elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.insertPlainText("\n")
            self._close_popups()
            self.set_height_for_block_counts()
            self._current_completion_state = CompletionState.empty()
            return True
        return False
    
    def _event_escape(self, event: QtGui.QKeyEvent):
        if self._list_widget.isVisible() or self._tooltip_widget.isVisible():
            self._close_popups()
        else:
            self.setText("")
            HistoryManager.instance().init_iterator()
        return True
        
    def event(self, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            assert isinstance(event, QtGui.QKeyEvent)
            done = self._keypress_event(event)
            if done:
                return True

        elif event.type() in _HIDE_POPUPS:
            self._close_popups()
        elif event.type() == QtCore.QEvent.Type.WindowDeactivate:
            if QtW.QApplication.activeWindow() not in (
                self._session.ui.main_window,
                self._tooltip_widget,
            ):
                # in this case, other application is activated
                self._close_popups()

        return super().event(event)

    def set_height_for_block_counts(self):
        nblocks = min(max(self.document().blockCount(), 1), 6)
        self.setFixedHeight((self.fontMetrics().height() + 2) * nblocks + 6)

    def _complete_with_current_item(self):
        comp = self._list_widget.currentItem().data(Qt.ItemDataRole.UserRole)
        self._complete_with(comp)

    def focusOutEvent(self, a0: QtGui.QFocusEvent) -> None:
        if QtW.QApplication.focusWidget():
            self._close_popups()
        return super().focusOutEvent(a0)

    def _close_popups(self):
        if self._list_widget.isVisible():
            self._list_widget.hide()
        if self._tooltip_widget.isVisible():
            self._tooltip_widget.hide()
        if self._inline_suggestion_widget.isVisible():
            self._inline_suggestion_widget.hide()
        return None

    def _close_tooltip_and_list(self):
        self._tooltip_widget.hide()
        self._list_widget.hide()

def _is_too_bottom(pos: int):
    screen_bottom = QtW.QApplication.primaryScreen().geometry().bottom()
    return pos > screen_bottom

_HIDE_POPUPS = {
    QtCore.QEvent.Type.Move,
    QtCore.QEvent.Type.Hide,
    QtCore.QEvent.Type.Resize,
    QtCore.QEvent.Type.WindowStateChange,
    QtCore.QEvent.Type.ZOrderChange,
}
