from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from ..types import WordInfo, resolve_cmd_desc
from ..type_map import parse_annotation
from .consts import ColorPreset

if TYPE_CHECKING:
    from .main import QCommandLineEdit, CompletionState

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
        self.setCurrentItem(item)
        self.parentWidget()._complete_with_current_item()

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        self.parentWidget().setFocus()
    
    def add_items_with_highlight(self, cmp: CompletionState):
        prefix = cmp.text
        
        # adjust item count
        for _ in range(len(cmp.completions) - self.count()):
            list_widget_item = QtW.QListWidgetItem()
            label = QtW.QLabel()
            self.addItem(list_widget_item)
            self.setItemWidget(list_widget_item, label)
        for _ in range(self.count() - len(cmp.completions)):
            self.takeItem(0)
        
        for _i, item in enumerate(cmp.completions):
            if item.startswith(prefix):
                prefix, item = item[:len(prefix)], item[len(prefix):]
            text = f"<b>{_colored(prefix, ColorPreset.MATCH)}</b>{item}"
            if cmp.info is not None:
                info = cmp.info[_i]
                text += f"  ({info})"
            list_widget_item = self.item(_i)
            label = self.itemWidget(list_widget_item)
            label.setText(text)
            list_widget_item.setData(Qt.ItemDataRole.UserRole, prefix + item)

    def set_row(self, idx: int):
        self.setCurrentRow(idx)
        self.scrollToItem(
            self.currentItem(), QtW.QAbstractItemView.ScrollHint.EnsureVisible
        )
        self.changed.emit(idx, self.currentItem().data(Qt.ItemDataRole.UserRole))

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
        self.setFixedWidth(320)
        self.setReadOnly(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
    
    def setWordInfo(self, word_info: WordInfo, command_name: str):
        cmd_desc = resolve_cmd_desc(word_info)
        if cmd_desc is None:
            self.setText("")
            self.hide()
            return None
        strings = [f"<b>{_colored(command_name, ColorPreset.COMMAND)}</b>"]
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