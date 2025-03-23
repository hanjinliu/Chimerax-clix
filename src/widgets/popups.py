from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from html import escape

from ..types import WordInfo, resolve_cmd_desc
from ..action import Action, CommandPaletteAction
from .._preference import load_preference
from .._utils import colored

if TYPE_CHECKING:
    from .cli_widget import QCommandLineEdit
    from ..completion import CompletionState

@dataclass
class ItemContent:
    text: str
    info: str
    action: Action

class QCompletionPopup(QtW.QListWidget):
    changed = QtCore.Signal(int, ItemContent)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemPressed.connect(self._on_item_clicked)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def parentWidget(self) -> QCommandLineEdit:
        return super().parentWidget()

    def resizeForContents(self):
        self.setFixedSize(
            self.sizeHintForColumn(0) + self.frameWidth() * 2,
            min(self.sizeHintForRow(0) * self.count() + self.frameWidth() * 2, 200),
        )

    def _on_item_clicked(self, item: QtW.QListWidgetItem):
        self.setCurrentItem(item)
        self.parentWidget()._complete_with_current_item()

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        self.parentWidget().setFocus()
    
    def add_items_with_highlight(self, cmp: CompletionState):
        prefix = cmp.text
        color_theme = load_preference(force=False).color_theme
        
        # adjust item count
        for _ in range(len(cmp.completions) - self.count()):
            list_widget_item = QtW.QListWidgetItem()
            label = QtW.QLabel()
            self.addItem(list_widget_item)
            self.setItemWidget(list_widget_item, label)
        for _ in range(self.count() - len(cmp.completions)):
            self.takeItem(0)

        if cmp.type == "command-palette":
            for _i, item in enumerate(cmp.completions):
                if not isinstance(action := cmp.action[_i], CommandPaletteAction):
                    continue
                list_widget_item = self.item(_i)
                list_widget_item.setToolTip(action.tooltip)
                list_widget_item.setText
                list_widget_item.setData(
                    Qt.ItemDataRole.UserRole,
                    ItemContent(cmp.text, "", cmp.action[_i]),
                )
        else:
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
                assert isinstance(label, QtW.QLabel)
                label.setText(text)
                list_widget_item.setData(
                    Qt.ItemDataRole.UserRole,
                    ItemContent(prefix + item, info, cmp.action[_i]),
                )

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

        
class QTooltipPopup(QtW.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(360)
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
    
    def setWordInfo(self, word_info: WordInfo, command_name: str):
        cmd_desc = resolve_cmd_desc(word_info)
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
