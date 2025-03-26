from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Iterator
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from html import escape

from ..types import WordInfo, resolve_cmd_desc
from ..algorithms.action import Action, CommandPaletteAction
from ..palette import command_palette_actions, color_text_by_match
from .._preference import load_preference
from .._utils import colored

if TYPE_CHECKING:
    from .cli_widget import QCommandLineEdit
    from ..algorithms import CompletionState

@dataclass
class ItemContent:
    text: str
    info: str
    action: Action
    type: str

class QSelectablePopup(QtW.QListWidget):
    changed = QtCore.Signal(int, ItemContent)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemPressed.connect(self._on_item_clicked)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QSelectablePopup::item:selected { background-color: #888888; }")
    
    def _on_item_clicked(self, item: QtW.QListWidgetItem):
        self.setCurrentItem(item)
        self.exec_current_item()
    
    def exec_current_item(self):
        """Must be implemented by subclasses."""
        raise NotImplementedError

    def parentWidget(self) -> QCommandLineEdit:
        return super().parentWidget()

    def resizeForContents(self):
        self.setFixedSize(
            self.sizeHintForColumn(0) + self.frameWidth() * 2,
            min(self.sizeHintForRow(0) * self.count() + self.frameWidth() * 2, 200),
        )

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        self.parentWidget().setFocus()
    
    def set_row(self, idx: int):
        self.setCurrentRow(idx)
        self.scrollToItem(
            self.currentItem(), QtW.QAbstractItemView.ScrollHint.EnsureVisible
        )
        if content := self.current_item_content():
            self.changed.emit(idx, content)

    def current_item_content(self) -> ItemContent:
        return self.currentItem().data(Qt.ItemDataRole.UserRole)

    def goto_next(self):
        self.set_row((self.currentRow() + 1) % self.count())

    def goto_next_page(self):
        h0 = self.sizeHintForRow(0)
        self.set_row(min(self.currentRow() + self.height() // h0, self.count() - 1))

    def goto_last(self):
        self.set_row(self.count() - 1)

    def goto_previous(self):
        self.set_row((self.currentRow() - 1) % self.count())

    def goto_previous_page(self):
        h0 = self.sizeHintForRow(0)
        self.set_row(max(self.currentRow() - self.height() // h0, 0))

    def goto_first(self):
        self.set_row(0)

    def adjust_item_count(self, num: int):        
        # adjust item count
        for _ in range(num - self.count()):
            list_widget_item = QtW.QListWidgetItem()
            label = QtW.QLabel()
            self.addItem(list_widget_item)
            self.setItemWidget(list_widget_item, label)
        for _ in range(self.count() - num):
            self.takeItem(0)

    if TYPE_CHECKING:
        def itemWidget(self, item: QtW.QListWidgetItem) -> QtW.QLabel | None:
            ...

class QCompletionPopup(QSelectablePopup):
    def add_items_with_highlight(self, cmp: CompletionState):
        prefix = cmp.text
        color_theme = load_preference(force=False).color_theme
        self.adjust_item_count(len(cmp.completions))

        for _i, item in enumerate(cmp.completions):
            if item.startswith(prefix):
                prefix, item = item[:len(prefix)], item[len(prefix):]
            else:
                prefix = ""
            if prefix:
                text = f"<b>{colored(prefix, color_theme.matched)}</b>{item}"
            else:
                text = item
            info = cmp.info[_i]
            if info:
                text += f" {info}"
            list_widget_item = self.item(_i)
            label = self.itemWidget(list_widget_item)
            label.setText(text)
            list_widget_item.setData(
                Qt.ItemDataRole.UserRole,
                ItemContent(
                    prefix + item,
                    info,
                    cmp.action[_i],
                    type=cmp.type,
                ),
            )
    
    def exec_current_item(self):
        comp = self.current_item_content()
        self.complete_with(comp.text, comp.type)
        comp.action.execute(self)

    def complete_with(self, comp: str, typ: str):
        parent = self.parentWidget()
        if "path" in typ.split(","):
            _n = len(parent._current_completion_state.text.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
        else:
            _n = len(parent._current_completion_state.text)
        text_to_comp = comp[_n:]
        parent.insertPlainText(text_to_comp)
        parent._update_completion_state(False)
        parent._close_popups()
        return None

class QCommandPalettePopup(QSelectablePopup):
    _max_matches = 60

    def add_items_with_highlight(self, cmp: CompletionState) -> None:
        """Update the list to match the input text."""
        max_matches = self._max_matches
        color_theme = load_preference(force=False).color_theme
        input_text = cmp.text
        row = 0
        count_before = self.count()
        for row, action in enumerate(self.iter_top_hits(input_text)):
            if count_before <= row:
                item = QtW.QListWidgetItem()
                current_label = QtW.QLabel()
                self.addItem(item)
                self.setItemWidget(item, current_label)
                count_before += 1
            else:
                item = self.item(row)
                current_label = self.itemWidget(item)
            current_label.setToolTip(action.tooltip)
            item.setData(
                Qt.ItemDataRole.UserRole,
                ItemContent(action.desc, action.tooltip, action, "command"),
            )
            label_txt = color_text_by_match(input_text, action.desc, color_theme.matched)
            current_label.setText(label_txt)
    
            if row >= max_matches:
                break
            row = row + 1

        for i in range(row, count_before):
            self.takeItem(row)
        return

    def iter_top_hits(self, input_text: str) -> Iterator[CommandPaletteAction]:
        """Iterate over the top hits for the input text"""
        commands: list[tuple[float, CommandPaletteAction]] = []
        for command in self.get_all_commands():
            score = _match_score(command.desc, input_text)
            if score > 0.0:
                commands.append((score, command))
        commands.sort(key=lambda x: x[0], reverse=True)
        for _, command in commands:
            yield command

    def exec_current_item(self):
        comp = self.current_item_content()
        self.parentWidget()._close_popups()
        comp.action.execute(self.parentWidget())

    @cache
    def get_all_commands(self) -> list[CommandPaletteAction]:
        return command_palette_actions(self.parentWidget()._session.ui.main_window)

def _match_score(command_text: str, input_text: str) -> float:
    """Return a match score (between 0 and 1) for the input text."""
    name = command_text.lower()
    if all(word in name for word in input_text.lower().split(" ")):
        return 1.0
    if len(input_text) < 4 and all(char in name for char in input_text.lower()):
        return 0.7
    return 0.0

        
class QTooltipPopup(QtW.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(360)
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
    
    def setWordInfo(self, word_info: WordInfo, command_name: str):
        cmd_desc = resolve_cmd_desc(word_info, command_name)
        color_theme = load_preference().color_theme
        if cmd_desc is None:
            self.setText("")
            self.hide()
            return None
        strings = [f"<b>{colored(command_name, color_theme.command)}</b>"]
        if cmd_desc.synopsis is not None:
            strings.append(cmd_desc.synopsis.replace("\n", "<br>"))
        strings.append(f"<br><u>{colored('Arguments', 'gray')}</u>")
        for name, typ in cmd_desc._required.items():
            strings.append(
                f"<b>{name}</b>: {colored(_as_name(typ), color_theme.type)}"
            )
        # here, some arguments are both optional and keyword
        keywords = cmd_desc._keyword.copy()
        for name, typ in cmd_desc._optional.items():
            annot = colored(_as_name(typ), color_theme.type)
            if name in keywords:
                strings.append(f"<b>{name}</b>: {annot} <i>(optional, keyword)</i>")
                keywords.pop(name)
            else:
                strings.append(f"<b>{name}</b>: {annot} <i>(optional)</i>")
        for name, typ in keywords.items():
            strings.append(
                f"<b>{name}</b>: {colored(_as_name(typ), color_theme.type)} "
                "<i>(keyword)</i>"
            )
        self.setText("<br>".join(strings))
        return None

def _as_name(typ):
    return escape(typ.name)
