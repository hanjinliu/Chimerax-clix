from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from ..algorithms.action import Action
from ..algorithms import CompletionState

if TYPE_CHECKING:
    from .cli_widget import QCommandLineEdit

@dataclass
class ItemContent:
    text: str
    info: str
    action: Action
    type: str

class QSelectablePopup(QtW.QListWidget):
    changed = QtCore.Signal(int, ItemContent)

    def __init__(self, parent=None):
        super().__init__()
        self.setParent(parent, Qt.WindowType.ToolTip)
        self.setFont(parent.font())
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

    def session(self):
        return self.parentWidget()._session
    
    def prep_item(self, row: int, count: int) -> tuple[QtW.QListWidgetItem, QtW.QLabel]:
        if count <= row:
            item = QtW.QListWidgetItem()
            current_label = QtW.QLabel()
            self.addItem(item)
            self.setItemWidget(item, current_label)
            count += 1
        else:
            item = self.item(row)
            current_label = self.itemWidget(item)
        return item, current_label
    
    def add_items_with_highlight(self, cmp: CompletionState) -> None:
        """Must be implemented by subclasses."""
        raise NotImplementedError

    def try_show_me(self):
        parent = self.parentWidget()
        parent._update_completion_state(allow_auto=False)
        self.add_items_with_highlight(parent._current_completion_state)
        parent._optimize_selectable_popup_geometry(self)
        if self.isVisible():
            self.setCurrentRow(0)
        if self.count() > 0:
            self.set_row(0)
        return None

    if TYPE_CHECKING:
        def itemWidget(self, item: QtW.QListWidgetItem) -> QtW.QLabel | None:
            ...