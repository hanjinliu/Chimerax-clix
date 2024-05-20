from __future__ import annotations

from typing import TYPE_CHECKING
import re
from qtpy import QtWidgets as QtW, QtCore, QtGui
from .._history import HistoryManager
from .consts import _FONT

if TYPE_CHECKING:
    from .cli_widget import QCommandLineEdit

_QFONT = QtGui.QFont(_FONT)

class QShowHistoryButton(QtW.QPushButton):
    def __init__(self, cli: QCommandLineEdit):
        super().__init__()
        self._cli_widget = cli
        self.setText("...")
        self.setToolTip("Show command history (Ctrl+H)")
        self.setShortcut("Ctrl+H")
        self.setFixedWidth(30)
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        self._hist_list_widget = QHistoryWidget(self)
        self._hist_list_widget.setWindowFlags(QtCore.Qt.WindowType.Popup)
        self._hist_list_widget.setFixedWidth(420)
        self._hist_list_widget.show()
        size = self._hist_list_widget.size()
        point = self.rect().topRight() - QtCore.QPoint(size.width(), size.height())
        self._hist_list_widget.move(self.mapToGlobal(point))
        self._hist_list_widget._filter._filter_line.setFocus()

class QHistoryListModel(QtCore.QAbstractListModel):
    def __init__(self, history, parent):
        super().__init__(parent)
        self._history = history

    def rowCount(self, parent=None):
        return len(self._history)

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._history[index.row()]
        elif role == QtCore.Qt.ItemDataRole.FontRole:
            return _QFONT
        elif role == QtCore.Qt.ItemDataRole.BackgroundRole:
            if index.row() == self.parent().currentIndex().row():
                return QtGui.QBrush(QtGui.QColor(232, 232, 255))
            if index.row() % 2 == 0:
                return QtGui.QBrush(QtGui.QColor(255, 255, 255))
            else:
                return QtGui.QBrush(QtGui.QColor(238, 238, 238))
        return None
    
    if TYPE_CHECKING:
        def parent(self) -> QHistoryList:
            return super().parent()

class QHistoryWidget(QtW.QWidget):
    def __init__(self, btn: QShowHistoryButton):
        super().__init__()
        self._layout = QtW.QVBoxLayout()
        self.setLayout(self._layout)
        
        self._filter = QHistoryFilter()
        self._history_list = QHistoryList(btn)
        self._layout.addWidget(self._filter)
        self._layout.addWidget(self._history_list)
        
        self.setMaximumHeight(500)

        @self._filter._filter_line.textChanged.connect
        def _cb(txt: str):
            if txt == "":
                self._history_list.set_list(HistoryManager.instance().aslist())
            texts = self._filter.run_filter(self._history_list._model._history)
            self._history_list.set_list(texts)
        
class QHistoryList(QtW.QListView):
    def __init__(self, parent: QShowHistoryButton) -> None:
        super().__init__(parent)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._btn = parent
        self.clicked.connect(self.update_with_current_command)
        self.set_list(HistoryManager.instance().aslist())
    
    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == QtCore.Qt.Key.Key_Return:
            self.update_with_current_command()
        else:
            super().keyPressEvent(e)

    def update_with_current_command(self):
        command = self.currentIndex().data(QtCore.Qt.ItemDataRole.DisplayRole)
        if isinstance(command, str):
            self._btn._cli_widget.setText(command)
            self.hide()
            cursor = self._btn._cli_widget.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            self._btn._cli_widget.setTextCursor(cursor)
            self._btn._hist_list_widget.hide()
    
    def set_list(self, hist: list[str]):
        self._model = QHistoryListModel(hist, self)
        self.setModel(self._model)
        self.scrollToBottom()
        self.setCurrentIndex(self._model.index(self._model.rowCount() - 1, 0))

class QFilterLineEdit(QtW.QLineEdit):
    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        if a0.key() in (
            QtCore.Qt.Key.Key_Up,
            QtCore.Qt.Key.Key_Down,
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.Key.Key_PageDown,
            QtCore.Qt.Key.Key_PageUp
        ):
            self.parentWidget().parentWidget()._history_list.keyPressEvent(a0)
            return None
        return super().keyPressEvent(a0)
    
class QHistoryFilter(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QtW.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        
        self._filter_line = QFilterLineEdit()
        
        self._method_choice = QtW.QComboBox()
        self._method_choice.addItems(["abc___", "___abc", "__abc__", ".*"])
        self._layout.addWidget(QtW.QLabel("Search:"))
        self._layout.addWidget(self._method_choice)
        self._layout.addWidget(self._filter_line)
        
        self._method_choice.currentIndexChanged.connect(lambda: self._filter_line.setFocus())
    
    def run_filter(self, texts: list[str]) -> list[str]:
        if self._method_choice.currentIndex() == 0:
            out = [text for text in texts if text.startswith(self._filter_line.text())]
        elif self._method_choice.currentIndex() == 1:
            out = [text for text in texts if text.endswith(self._filter_line.text())]
        elif self._method_choice.currentIndex() == 2:
            out = [text for text in texts if self._filter_line.text() in text]
        else:
            out = [text for text in texts if re.match(self._filter_line.text(), text) is not None]
        return out
