from __future__ import annotations

from typing import NamedTuple

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from ..types import WordInfo, resolve_cmd_desc
from .._history import HistoryManager
from chimerax.core.commands import run
from .consts import _FONT, ColorPreset
from ._utils import colored
from .popups import QCompletionPopup, QTooltipPopup
from .highlighter import QCommandHighlighter

class CompletionState(NamedTuple):
    text: str
    completions: list[str]
    command: str | None = None
    info: list[str] | None = None
    
    @classmethod
    def empty(cls) -> CompletionState:
        return cls("", [])

class QSuggestionLabel(QtW.QLabel):
    pass

class QCommandLineEdit(QtW.QTextEdit):
    def __init__(self, commands: dict[str, WordInfo], session):
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
        self._history_mgr = HistoryManager()
        self._text_removed_last = False

    def _update_completion_state(self, allow_auto: bool = False) -> bool:
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine, QtGui.QTextCursor.MoveMode.KeepAnchor)
        self._current_completion_state = self._get_completion_list(cursor.selectedText())
        if len(self._current_completion_state.completions) == 0:
            return False
        if len(self._current_completion_state.completions) == 1 and allow_auto:
            self._complete_with(self._current_completion_state.completions[0])
        return True

    def show_completion(self, allow_auto: bool = True):
        if self._list_widget.isVisible():
            self._complete_with_current_item()
            return
        if not self._update_completion_state(allow_auto):
            return
        self._create_list_widget()
    
    def text(self) -> str:
        nchars = self._history_mgr.suggestion_char_count()
        text = self.toPlainText()
        if nchars > 0:
            text = text[:-nchars]
        return text.replace("\u2029", "\n")

    def run_command(self):
        code = self.text()
        try:
            for line in code.split("\n"):
                if line.strip() == "":
                    continue
                run(self._session, line)
        finally:
            self.setText("")
        if code:
            self._history_mgr.add_code(code)

    def _adjust_tooltip_for_list(self, idx: int):
        item_rect = self._list_widget.visualItemRect(self._list_widget.item(idx))
        rect = self._list_widget.rect()
        rel_dist_from_bottom = (rect.bottom() - item_rect.bottom()) / rect.height()
        item_rect.setX(item_rect.x() + 10)
        if rel_dist_from_bottom > 0.5:
            pos = item_rect.topRight()
        else:
            pos = item_rect.bottomRight() - QtCore.QPoint(0, self._tooltip_widget.height())
        self._tooltip_widget.move(self._list_widget.mapToGlobal(pos))

    def _list_selection_changed(self, idx: int, text: str):
        if winfo := self._commands.get(text, None):
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
        suggestion_widget.setStyleSheet("QSuggestionLabel { background-color: #ffffff; }")
        suggestion_widget.hide()
        return suggestion_widget

    def _get_completion_list(self, text: str) -> CompletionState:
        if text == "":
            return CompletionState(text, [])

        # command completion
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
            elif text_strip.startswith(command_name):
                current_command = command_name
        if len(matched_commands) > 0:
            if len(matched_commands) == 1 and matched_commands[0] == text_strip:
                # not need to show the completion list
                pass
            elif " " not in text:
                # if `matched_commands` is
                #   toolshed list
                #   toolshed install
                # then `base_commands` is
                #   toolshed
                base_commands: dict[str, None] = {}  # ordered set
                for cmd in matched_commands:
                    base_commands[cmd.split(" ")[0]] = None
                matched_commands = list(base_commands.keys()) + matched_commands
            return CompletionState(text, matched_commands, current_command)
    
        # attribute completion
        *pref, last_word = text.rsplit(" ")
        if pref == [] or last_word == "":
            return CompletionState(text, [], current_command)
        if last_word.startswith("#"):
            return self._completion_for_model(last_word, current_command)
        if last_word.startswith("/"):
            return self._completion_for_chain(last_word, current_command)

        cmd = current_command or self._current_completion_state.command
        if winfo := self._commands.get(cmd, None):
            comp_list: list[str] = []
            cmd_desc = resolve_cmd_desc(winfo)
            if cmd_desc is None:
                return CompletionState(text, [], current_command)
            for _k in cmd_desc._keyword.keys():
                if _k.startswith(last_word):
                    comp_list.append(_k)
            return CompletionState(
                last_word, comp_list, current_command, ["<i>keyword</i>"] * len(comp_list)
            )
        return CompletionState(text, [], current_command)

    def _completion_for_model(self, last_word: str, current_command: str | None):
        # model ID completion
        # "#" -> "#1 (model name)" etc.
        # try model+chain specifiction completion such as "#1/B"
        if "/" in last_word:
            model_spec, chain_spec = last_word.split("/", 1)
            for model in self._session.models.list():
                if _model_to_spec(model) == model_spec:
                    with_chain_ids: list[str] = list(
                        f"{model_spec}/{_i}" for _i in model.chains.chain_ids
                        if _i.startswith(chain_spec)
                    )
                    return CompletionState(
                        last_word, with_chain_ids, current_command, 
                        ["<i>chain ID</i>"] * len(with_chain_ids)
                    )
        comps = []
        info = []
        for model in self._session.models.list():
            spec = _model_to_spec(model)
            if spec.startswith(last_word):
                comps.append(_model_to_spec(model))
                info.append(model.name)
        return CompletionState(last_word, comps, current_command, info)

    def _completion_for_chain(self, last_word: str, current_command: str | None):
        # collect all the available chain IDs
        all_chain_ids: set[str] = set()
        for model in self._session.models.list():
            all_chain_ids.update(
                f"/{_i}" for _i in model.chains.chain_ids if _i.startswith(last_word[1:])
            )
        all_chain_ids = sorted(all_chain_ids)
        # Now, all_chain_ids is like ["/A", "/B", ...]
        return CompletionState(
            last_word, all_chain_ids, current_command, 
            ["<i>chain ID</i>"] * len(all_chain_ids)
        )

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
        else:
            name = self._current_completion_state.command
            cmd = self._commands[name]
            self._tooltip_widget.setWordInfo(cmd, name)
            self._try_show_tooltip_widget()
        
        # resize the widget
        self.set_height_for_block_counts()
        
        # one-line suggestion
        if not self._text_removed_last:
            this_line = self.textCursor().block().text()
            if suggested := self._history_mgr.suggest(this_line):
                self._show_inline_suggestion(suggested)
        return None
    
    def _show_inline_suggestion(self, suggested: str):
        self._inline_suggestion_widget.setText(colored(suggested, ColorPreset.SUGGESTION))
        cursor_rect = self.cursorRect()
        label_height = QtGui.QFontMetrics(self.font()).height()
        cursor_height = cursor_rect.height()
        dh = (cursor_height - label_height) // 2
        tr = cursor_rect.topRight()
        cursor_point = QtCore.QPoint(tr.x(), tr.y() + dh)
        self._inline_suggestion_widget.move(self.mapToGlobal(cursor_point))
        self._inline_suggestion_widget.show()
        return None

    def _apply_inline_suggestion(self):
        cursor = self.textCursor()
        if sug := self._history_mgr.pop_suggestion():
            self.insertPlainText(sug)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
        self._inline_suggestion_widget.hide()
        self._close_popups()
        return True

    def _try_show_list_widget(self):
        self._update_completion_state(allow_auto=False)
        text = self._current_completion_state.text
        items = self._current_completion_state.completions
        if len(items) == 0 or len(text) == 0:
            self._list_widget.hide()
            return
        self._list_widget.add_items_with_highlight(self._current_completion_state)
        if not self._list_widget.isVisible():
            self._list_widget.show()
        self._list_widget.move(self.mapToGlobal(self.cursorRect().bottomLeft()))
        self._list_widget.resizeForContents()
        return
    
    def _try_show_tooltip_widget(self):
        if not self._tooltip_widget.isVisible() and self._tooltip_widget.toPlainText() != "":
            self._tooltip_widget.show()
            self.setFocus()
        if self._tooltip_widget.isVisible():
            if self._list_widget.isVisible():
                # show next to the cursor
                self._adjust_tooltip_for_list(self._list_widget.currentRow())
            else:
                # show beside the completion list
                self._tooltip_widget.move(self.mapToGlobal(self.cursorRect().bottomRight()))
        return None

    def _complete_with(self, comp: str):
        _n = len(self._current_completion_state.text)
        self.insertPlainText(comp[_n:])
        self._update_completion_state(False)
        self._close_popups()
        return None

    def event(self, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            assert isinstance(event, QtGui.QKeyEvent)
            self._text_removed_last = False
            if event.key() == Qt.Key.Key_Tab:
                self.show_completion()
                return True
            # up/down arrow keys
            elif event.key() == Qt.Key.Key_Down:
                if self._list_widget.isVisible():
                    if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                        self._list_widget.goto_next()
                    elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                        self._list_widget.goto_last()
                    else:
                        return False
                    return True
                cursor = self.textCursor()
                if cursor.blockNumber() == self.document().blockCount() - 1:
                    self.setText(self._history_mgr.look_for_next(self.text()))
                    self.setTextCursor(cursor)
                    return True
            elif event.key() == Qt.Key.Key_PageDown:
                if self._list_widget.isVisible():
                    self._list_widget.goto_next_page()
                    return True
            elif event.key() == Qt.Key.Key_Up:
                if self._list_widget.isVisible():
                    if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                        self._list_widget.goto_previous()
                    elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                        self._list_widget.goto_first()
                    else:
                        return False
                    return True
                cursor = self.textCursor()
                if cursor.blockNumber() == 0:
                    self.setText(self._history_mgr.look_for_prev(self.text()))
                    self.setTextCursor(cursor)
                    return True
            elif event.key() == Qt.Key.Key_PageUp:
                if self._list_widget.isVisible():
                    self._list_widget.goto_previous_page()
                    return True
            
            # left/right arrow keys
            elif event.key() == Qt.Key.Key_Right:
                cursor = self.textCursor()
                if cursor.atBlockEnd() and self._inline_suggestion_widget.isVisible():
                    self._apply_inline_suggestion()
                    return True
            elif event.key() == Qt.Key.Key_End:
                self._apply_inline_suggestion()
                return True

            elif event.key() == Qt.Key.Key_Return:
                if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                    if self._list_widget.isVisible():
                        self._complete_with_current_item()
                    else:
                        self.run_command()
                        self._history_mgr.init_iterator()
                    return True
                elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    self.insertPlainText("\n")
                    self._close_popups()
                    self.set_height_for_block_counts()
                    self._current_completion_state = CompletionState.empty()
                    return True
            elif event.key() == Qt.Key.Key_Escape:
                if self._list_widget.isVisible() or self._tooltip_widget.isVisible():
                    self._close_popups()
                    return True
                else:
                    self.setText("")
                    self._history_mgr.init_iterator()
                return True
            
            elif event.key() == Qt.Key.Key_Backspace:
                self._text_removed_last = True
            elif event.key() == Qt.Key.Key_Delete:
                self._text_removed_last = True
            elif event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._text_removed_last = True

        elif event.type() == QtCore.QEvent.Type.Move:
            self._close_popups()
        return super().event(event)

    def set_height_for_block_counts(self):
        nblocks = min(max(self.document().blockCount(), 1), 6)
        self.setFixedHeight((self.fontMetrics().height() + 2) * nblocks + 6)

    def _complete_with_current_item(self):
        comp = self._list_widget.currentItem().data(Qt.ItemDataRole.UserRole)
        self._complete_with(comp)

    def focusOutEvent(self, a0: QtGui.QFocusEvent) -> None:
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

def _model_to_spec(model):
    return "#" + ".".join(str(_id) for _id in model.id)
