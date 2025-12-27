from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from .consts import _FONT
from ._base import is_too_bottom
from .popups import QCompletionPopup, QCommandPalettePopup, QRecentFilePopup, QTooltipPopup, QSelectablePopup
from .highlighter import QCommandHighlighter
from ..types import WordInfo, resolve_cmd_desc, Mode
from .._history import HistoryManager
from ..algorithms import CompletionState, Context
from .._utils import colored
from .._preference import Preference
from .. import _injection as _inj
from .._cli_utils import iter_all_commands

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
        self.setPlaceholderText(
            "Run command here. Type '>' to enter action search mode. Type '/' to enter "
            "recent file mode."
        )
        self.textChanged.connect(self._on_text_changed)
        self._commands = commands
        self._mode = Mode.CLI
        self._current_completion_state = CompletionState.empty()
        self._list_widgets: dict[Mode, QSelectablePopup] = {
            Mode.CLI: QCompletionPopup(self),
            Mode.PALETTE: QCommandPalettePopup(self),
            Mode.RECENT: QRecentFilePopup(self),
        }
        self._tooltip_widget = self._create_tooltip_widget()
        self._inline_suggestion_widget = self._create_suggestion_widget()
        self._session = session
        self._highlighter = QCommandHighlighter(self)
        self.set_height_for_block_counts()
        self._dont_need_inline_suggestion = False
        self._preference = preference
    
    def get_context(self, winfo: WordInfo) -> Context:
        return Context(
            models=self._session.models.list(),
            selectors=_inj.chimerax_selectors(),
            colors=_inj.chimerax_builtin_colors(),
            wordinfo=winfo,
            filter_volume=_inj.chimerax_filter_volume,
            filter_surface=_inj.chimerax_filter_surface,
            filter_atom=_inj.chimerax_filter_atom,
            filter_pseudo_bond=_inj.chimerax_filter_pseudo_bond,
            filter_bond=_inj.chimerax_filter_bond,
            get_file_open_mode=_inj.chimerax_get_mode,
            get_file_list=_inj.chimerax_file_history(self._session),
            run_command=_inj.chimerax_run(self._session),
        )
    
    def clear_completion_state(self):
        """Clear the current completion state."""
        self._current_completion_state = CompletionState.empty()

    def _update_completion_state(self, allow_auto: bool = False) -> bool:
        plain_text = self.toPlainText()
        old_mode = self._mode
        if plain_text.startswith(">"):
            self._mode = Mode.PALETTE
        elif plain_text.startswith("/"):
            self._mode = Mode.RECENT
        else:
            self._mode = Mode.CLI

        # need to rehighlight if the mode is changed
        if old_mode is not self._mode:
            self._highlighter.rehighlight()
        
        list_widget = self._current_popup()
        if self._mode is Mode.PALETTE:
            self._current_completion_state = CompletionState(plain_text[1:], [])
        elif self._mode is Mode.RECENT:
            self._current_completion_state = CompletionState(plain_text[1:], [])
        else:
            assert isinstance(list_widget, QCompletionPopup)
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine, QtGui.QTextCursor.MoveMode.KeepAnchor)
            self._current_completion_state = list_widget._get_completion_list(cursor.selectedText())
            if len(self._current_completion_state.completions) == 0:
                return False
            if len(self._current_completion_state.completions) == 1 and allow_auto:
                state = self._current_completion_state
                list_widget.complete_with(state.completions[0], state.type)
        return True

    def text(self) -> str:
        text = self.toPlainText()
        return text.replace("\u2029", "\n")

    def run_command(self):
        """Run the command in the line edit."""
        code = self.text().rstrip()
        if code == "":
            return None
        if code.endswith("?"):
            self._open_help_viewer(code[:-1].strip())
            self.setText("")
            return None
        ctx = self.get_context(None)
        try:
            for line in code.split("\n"):
                if (line := line.strip()) == "":
                    continue
                ctx.run_command(line)
                self._update_alias(line)  # If alias is set, update the library
                self._update_namespace(line)
        except Exception:
            HistoryManager.instance().init_iterator(last=code)
            raise
        else:
            if code:
                HistoryManager.instance().add_code(code)
            HistoryManager.instance().init_iterator()
        finally:
            self.setText("")
            self.clear_completion_state()

    def _open_help_viewer(self, code: str):
        from chimerax.help_viewer import show_url  # type: ignore
            
        if command := self._commands.get(code, None):
            if out := resolve_cmd_desc(command, code):
                if out.url:
                    show_url(self._session, out.url)
            else:
                raise ValueError(f"Command {code!r} does not have CmdDesc.")
        else:
            raise ValueError(f"Command {code!r} not found.")
        return None

    def _adjust_tooltip_for_list(self, idx: int):
        """Move the tooltip popup next to the list widget."""
        list_widget = self._current_popup()
        item_rect = list_widget.visualItemRect(list_widget.item(idx))
        pos = list_widget.mapToGlobal(item_rect.topRight())
        if is_too_bottom(pos.y() + self._tooltip_widget.height()):
            pos = list_widget.mapToGlobal(
                item_rect.bottomRight() - QtCore.QPoint(0, self._tooltip_widget.height())
            )
        pos.setX(pos.x() + 10)
        self._tooltip_widget.move(pos)

    def _show_popup_widget(self, popup: QSelectablePopup):
        """Show specified popup and hide others"""
        for each_widget in self._list_widgets.values():
            if each_widget is not popup:
                each_widget.hide()
            else:
                each_widget.try_show_me()

    def _on_text_changed(self):
        self._inline_suggestion_widget.hide()
        # resize the widget
        self.set_height_for_block_counts()

        # look for the completion
        self._update_completion_state(False)
        list_widget = self._current_popup()
        self._show_popup_widget(list_widget)
        list_widget.post_show_me()
    
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

    def _apply_inline_suggestion(self):
        """Accept the inline suggestion and update the line edit."""
        cursor = self.textCursor()
        if not cursor.atEnd():
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
        if sug := HistoryManager.instance().pop_suggestion():
            self.insertPlainText(sug)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
            self.setTextCursor(cursor)
        self._inline_suggestion_widget.hide()
        self._close_popups()

    def _optimize_selectable_popup_geometry(self, popup: QSelectablePopup):
        popup.resizeForContents()
        if not popup.isVisible():
            popup.show()
        _height = popup.height()
        pos = self.mapToGlobal(self.cursorRect().bottomLeft())
        if is_too_bottom(_height + pos.y()):
            pos = self.mapToGlobal(self.cursorRect().topLeft()) - QtCore.QPoint(0, _height)
        popup.move(pos)
    
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
        elif event.key() == Qt.Key.Key_W and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            done = self._event_delete_word(event)
        return done

    def _event_tab(self, event: QtGui.QKeyEvent):
        list_widget = self._current_popup()
        if self._mode is Mode.CLI:
            if list_widget.isVisible():
                list_widget.exec_current_item()
            elif not self._update_completion_state(True):
                pass
            else:
                self._show_popup_widget(list_widget)
        else:
            if list_widget.isVisible():
                list_widget.goto_next()
        return True
    
    def _event_paste(self, event: QtGui.QKeyEvent):
        self.clear_completion_state()
        # if html is pasted, converted it to a plain text
        clip = QtW.QApplication.clipboard()
        text = clip.text()
        self.insertPlainText(text)
        return True
    
    def _event_delete_word(self, event: QtGui.QKeyEvent):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.PreviousWord, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        return True

    def _event_down(self, event: QtGui.QKeyEvent):
        self._dont_need_inline_suggestion = True
        if self._current_popup().isVisible():
            if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                self._current_popup().goto_next()
            elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._current_popup().goto_last()
            else:
                return super().event(event)
            return True
        cursor = self.textCursor()
        if cursor.blockNumber() == self.document().blockCount() - 1:
            mgr = HistoryManager.instance()
            self.setText(mgr.look_for_next(self.text()))
            self.setTextCursor(cursor)
            if not mgr._is_searching:
                self.clear_completion_state()
            return True
        self._close_tooltip_and_list()
        return False
    
    def _event_page_down(self, event: QtGui.QKeyEvent):
        self._inline_suggestion_widget.hide()
        self._dont_need_inline_suggestion = True
        if self._current_popup().isVisible():
            self._current_popup().goto_next_page()
            return True
        self._close_tooltip_and_list()
    
    def _event_up(self, event: QtGui.QKeyEvent):
        self._inline_suggestion_widget.hide()
        self._dont_need_inline_suggestion = True
        if self._current_popup().isVisible():
            if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                self._current_popup().goto_previous()
            elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._current_popup().goto_first()
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
        if self._current_popup().isVisible():
            self._current_popup().goto_previous_page()
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
            list_widget = self._current_popup()
            if self._mode is Mode.CLI:
                if list_widget.isVisible() and self._preference.enter_completion:
                    list_widget.exec_current_item()
                else:
                    self.run_command()
            else:
                list_widget.exec_current_item()
            return True
        elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.insertPlainText("\n")
            self._close_popups()
            self.set_height_for_block_counts()
            self.clear_completion_state()
            return True
        return False
    
    def _event_escape(self, event: QtGui.QKeyEvent):
        if (
            any(w.isVisible() for w in self._list_widgets.values())
            or self._tooltip_widget.isVisible()
        ):
            self._close_popups()
        else:
            self.setText("")
            HistoryManager.instance().init_iterator()
        return True
    
    def _current_popup(self) -> QSelectablePopup:
        return self._list_widgets[self._mode]
        
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
        self.verticalScrollBar().setVisible(nblocks > 2)

    def focusOutEvent(self, a0: QtGui.QFocusEvent) -> None:
        if QtW.QApplication.focusWidget():
            self._close_popups()
        return super().focusOutEvent(a0)

    def _close_popups(self):
        self._close_tooltip_and_list()
        self._inline_suggestion_widget.hide()
        return None

    def _close_tooltip_and_list(self):
        self._tooltip_widget.hide()
        for widget in self._list_widgets.values():
            widget.hide()

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

    def _update_alias(self, line: str):
        """Update the command registry for alias changes."""
        if line.startswith(("~alias ", "alias ")):
            # NOTE: this is not the most efficient way, but is "safest"
            self._commands = dict(iter_all_commands())
         
    def _update_namespace(self, line: str):
        """Update the command registry for namespace changes."""
        if line.startswith("name "):
            _inj.chimerax_selectors.clear_cache()
            _inj.chimerax_selectors()  # create cache here

_HIDE_POPUPS = {
    QtCore.QEvent.Type.Move,
    QtCore.QEvent.Type.Hide,
    QtCore.QEvent.Type.Resize,
    QtCore.QEvent.Type.WindowStateChange,
    QtCore.QEvent.Type.ZOrderChange,
}
