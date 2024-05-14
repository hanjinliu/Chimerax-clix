from __future__ import annotations

import sys
from typing import NamedTuple

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from .types import WordInfo, resolve_cmd_desc
from .type_map import parse_annotation
from chimerax.core.commands import run

if sys.platform == "win32":
    _FONT = "Consolas"
elif sys.platform == "darwin":
    _FONT = "Menlo"
else:
    _FONT = "Monospace"

class ColorPreset:
    TYPE = "#28E028"
    MATCH = "#3C6CED"
    COMMAND = "#AF7500"
    MODEL = "#CF2424"
    KEYWORD = "#808080"

class QCompletionPopup(QtW.QListWidget):
    changed = QtCore.Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.itemClicked.connect(self._on_item_clicked)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def parentWidget(self) -> QCommandLineEdit:
        return super().parentWidget()

    def resizeForContents(self):
        self.setFixedSize(
            self.sizeHintForColumn(0) + self.frameWidth() * 2,
            min(self.sizeHintForRow(0) * self.count() + self.frameWidth() * 2, 200),
        )

    def _on_item_clicked(self, item: QtW.QListWidgetItem):
        self.parentWidget()._complete_with_current_item()

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        self.parentWidget().setFocus()
    
    def add_items_with_highlight(self, items: list[str], prefix: str):
        for item in items:
            list_widget_item = QtW.QListWidgetItem()
            if item.startswith(prefix):
                prefix, item = item[:len(prefix)], item[len(prefix):]
            label = QtW.QLabel(f"<b>{_colored(prefix, ColorPreset.MATCH)}</b>{item}")
            list_widget_item.setData(Qt.ItemDataRole.UserRole, prefix + item)
            self.addItem(list_widget_item)
            self.setItemWidget(list_widget_item, label)

    def goto_next(self):
        self.setCurrentRow((self.currentRow() + 1) % self.count())

    def goto_next_page(self):
        h0 = self.sizeHintForRow(0)
        self.setCurrentRow(
            min(self.currentRow() + self.height() // h0, self.count() - 1)
        )

    def goto_last(self):
        self.setCurrentRow(self.count() - 1)

    def goto_previous(self):
        self.setCurrentRow((self.currentRow() - 1) % self.count())

    def goto_previous_page(self):
        h0 = self.sizeHintForRow(0)
        self.setCurrentRow(max(self.currentRow() - self.height() // h0, 0))

    def goto_first(self):
        self.setCurrentRow(0)

    def currentChanged(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex):
        idx = current.row()
        if item := self.item(idx):
            text = item.data(Qt.ItemDataRole.UserRole)
            self.changed.emit(idx, text)
        
class QTooltipPopup(QtW.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
    
    def setWordInfo(self, word_info: WordInfo):
        cmd_desc = resolve_cmd_desc(word_info)
        if cmd_desc is None:
            self.setText("")
            return None
        strings: list[str] = []
        if cmd_desc.synopsis is not None:
            strings.append(cmd_desc.synopsis.replace("\n", "<br>"))
        for name, typ in cmd_desc._required.items():
            strings.append(
                f"<b>{name}</b>: {_colored(parse_annotation(typ), ColorPreset.TYPE)}"
            )
        for name, typ in cmd_desc._optional.items():
            strings.append(
                f"<b>{name}</b>: {_colored(parse_annotation(typ), ColorPreset.TYPE)} "
                "<i>(optional)</i>"
            )
        for name, typ in cmd_desc._keyword.items():
            strings.append(
                f"<b>{name}</b>: {_colored(parse_annotation(typ), ColorPreset.TYPE)} "
                "<i>(keyword)</i>"
            )
        self.setText("<br>".join(strings))
        return None

def _colored(text: str, color: str) -> str:
    return f"<font color=\"{color}\">{text}</font>"

class CompletionState(NamedTuple):
    text: str
    completions: list[str]
    command: str | None = None
    
    @classmethod
    def empty(cls) -> CompletionState:
        return cls("", [])


class QCommandLineEdit(QtW.QTextEdit):
    def __init__(self, commands: dict[str, WordInfo], session):
        super().__init__()
        self.setFont(QtGui.QFont(_FONT))
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.textChanged.connect(self._on_text_changed)
        self._commands = commands
        self._current_completion_state = CompletionState.empty()
        self._list_widget = None
        self._tooltip_widget = None
        self._session = session
        self._highlighter = QCommandHighlighter(self)
        self.set_height_for_block_counts()

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
        if self._list_widget is not None:
            self._complete_with_current_item()
            return
        if not self._update_completion_state(allow_auto):
            return
        self._create_list_widget()
    
    def text(self) -> str:
        return self.toPlainText().replace("\u2029", "\n")

    def run_command(self):
        for line in self.text().split("\n"):
            if line.strip() == "":
                continue
            run(self._session, line)
        self.setText("")

    def _list_selection_changed(self, idx: int, text: str):
        if winfo := self._commands.get(text, None):
            if self._tooltip_widget is None:
                self._create_tooltip_widget()
            item_rect = self._list_widget.visualItemRect(self._list_widget.item(idx))
            item_rect.setX(item_rect.x() + 12)
            self._tooltip_widget.move(self._list_widget.mapToGlobal(item_rect.topRight()))
            self._tooltip_widget.setWordInfo(winfo)
        
    def _create_list_widget(self):
        list_widget = QCompletionPopup()
        list_widget.setParent(self, Qt.WindowType.ToolTip)
        list_widget.setFont(self.font())
        items = self._current_completion_state.completions
        list_widget.add_items_with_highlight(items, self._current_completion_state.text)
        if len(items) == 0:
            # don't show the list widget if there are no items
            return
        list_widget.resizeForContents()
        list_widget.move(self.mapToGlobal(self.cursorRect().bottomRight()))
        list_widget.changed.connect(self._list_selection_changed)
        list_widget.show()
        self._list_widget = list_widget
        self.setFocus()
    
    def _create_tooltip_widget(self):
        tooltip_widget = QTooltipPopup()
        tooltip_widget.setParent(self, Qt.WindowType.ToolTip)
        tooltip_widget.setFont(self.font())
        if self._list_widget is not None and self._list_widget.isVisible():
            corner = self._list_widget.rect().topRight()
            corner.setX(corner.x() + 12)
            tooltip_widget.move(
                self._list_widget.mapToGlobal(corner)
            )
        else:
            tooltip_widget.move(self.mapToGlobal(self.cursorRect().bottomRight()))
        tooltip_widget.show()
        self._tooltip_widget = tooltip_widget
        self.setFocus()

    def _get_completion_list(self, text: str) -> CompletionState:
        if text == "":
            return CompletionState(text, [])

        # command completion
        matched_commands: list[str] = []
        current_command: str | None = None
        for command_name in self._commands.keys():
            if command_name.startswith(text.lstrip()):
                # if `text` is "toolshed", add
                #   toolshed list
                #   toolshed install ...
                # to `matched_commands`
                matched_commands.append(command_name)
            elif text.strip().startswith(command_name):
                current_command = command_name
        
        if len(matched_commands) > 0:
            if len(matched_commands) == 1 and matched_commands[0] == text.strip():
                # not need to show the completion list
                pass
            elif " " not in text:
                # if `matched_commands` is
                #   toolshed list
                #   toolshed install
                # then `base_commands` is
                #   toolshed
                base_commands: dict[str, None] = {}
                for cmd in matched_commands:
                    base_commands[cmd.split(" ")[0]] = None
                matched_commands = list(base_commands.keys()) + matched_commands
            return CompletionState(text, matched_commands, current_command)
    
        # attribute completion
        *pref, last_word = text.rsplit(" ")
        if pref == [] or last_word == "":
            return CompletionState(text, [], current_command)
        if winfo := self._commands.get(" ".join(pref).strip(), None):
            comp_list: list[str] = []
            cmd_desc = resolve_cmd_desc(winfo)
            if cmd_desc is None:
                return CompletionState(text, [], current_command)
            for _k in cmd_desc._keyword.keys():
                if _k.startswith(last_word):
                    comp_list.append(_k)
            return CompletionState(last_word, comp_list, current_command)
        return CompletionState(text, [], current_command)

    def _on_text_changed(self):
        if self._list_widget is None:
            if self._update_completion_state(False):
                self._create_list_widget()
        self._try_show_list_widget()
        if self._list_widget is not None:
            self._list_widget.setCurrentRow(0)

        if self._current_completion_state.command is None:
            if self._tooltip_widget is not None:
                self._tooltip_widget.deleteLater()
                self._tooltip_widget = None
        else:
            self._try_show_tooltip_widget()
            cmd = self._commands[self._current_completion_state.command]
            self._tooltip_widget.setWordInfo(cmd)
        self.set_height_for_block_counts()
        return None

    def _try_show_list_widget(self):
        if self._list_widget is not None:
            self._update_completion_state(allow_auto=False)
            text = self._current_completion_state.text
            self._list_widget.clear()
            items = self._current_completion_state.completions
            if len(items) == 0 or len(text) == 0:
                self._list_widget.close()
                self._list_widget = None
                return
            self._list_widget.add_items_with_highlight(items, text)
            self._list_widget.move(self.mapToGlobal(self.cursorRect().bottomLeft()))
            self._list_widget.resizeForContents()
        return
    
    def _try_show_tooltip_widget(self):
        if self._tooltip_widget is not None:
            self._tooltip_widget.deleteLater()
            self._tooltip_widget = None
        self._tooltip_widget = None
        self._create_tooltip_widget()
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
            if event.key() == Qt.Key.Key_Tab:
                self.show_completion()
                return True
            elif event.key() == Qt.Key.Key_Down:
                if self._list_widget is not None:
                    if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                        self._list_widget.goto_next()
                    elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                        self._list_widget.goto_last()
                    else:
                        return False
                    return True
            elif event.key() == Qt.Key.Key_PageDown:
                if self._list_widget is not None:
                    self._list_widget.goto_next_page()
                    return True
            elif event.key() == Qt.Key.Key_Up:
                if self._list_widget is not None:
                    if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                        self._list_widget.goto_previous()
                    elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                        self._list_widget.goto_first()
                    else:
                        return False
                    return True
                # TODO: search for the history

            elif event.key() == Qt.Key.Key_PageUp:
                if self._list_widget is not None:
                    self._list_widget.goto_previous_page()
                    return True
            elif event.key() == Qt.Key.Key_Return:
                if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                    if self._list_widget is not None:
                        self._complete_with_current_item()
                    else:
                        self.run_command()
                    return True
                elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    self.insertPlainText("\n")
                    self._close_popups()
                    self.set_height_for_block_counts()
                    self._current_completion_state = CompletionState.empty()
                    return True
            elif event.key() == Qt.Key.Key_Escape:
                if self._list_widget is not None or self._tooltip_widget is not None:
                    self._close_popups()
                    return True
                if self.text():
                    self.setText("")
                    return True
            
        elif event.type() == QtCore.QEvent.Type.Move:
            if self._list_widget is not None:
                self._list_widget.close()
                self._list_widget = None
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
        if self._list_widget is not None:
            self._list_widget.deleteLater()
            self._list_widget = None
        if self._tooltip_widget is not None:
            self._tooltip_widget.deleteLater()
            self._tooltip_widget = None
        return None

class QCommandHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent: QCommandLineEdit):
        super().__init__(parent.document())
        self._command_strings = set(parent._commands.keys())
    
    def highlightBlock(self, text: str):
        cur_command = []
        cur_start = 0
        cur_stop = 0
        for word in text.split(" "):
            if word != "":
                cur_command.append(word)
            next_stop = cur_stop + len(word)
            if " ".join(cur_command) in self._command_strings:
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(QtGui.QColor(ColorPreset.COMMAND))
                fmt.setFontWeight(QtGui.QFont.Weight.Bold)
                self.setFormat(cur_start, next_stop, fmt)
                cur_start = next_stop + 1
            elif word.startswith("#"):
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(QtGui.QColor(ColorPreset.MODEL))
                self.setFormat(cur_start, next_stop, fmt)
                cur_start = next_stop + 1
            else:
                self.setFormat(cur_start, next_stop, QtGui.QTextCharFormat())
            cur_stop += len(word) + 1
            
        return None
