from __future__ import annotations

from pathlib import Path
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
        self._hist_list_widget = None

    def _on_clicked(self):
        self._hist_list_widget = QHistoryWidget(self)
        self._hist_list_widget.setWindowFlags(QtCore.Qt.WindowType.Popup)
        self._hist_list_widget.setFixedWidth(420)
        try:
            bg_color = self._cli_widget.palette().color(QtGui.QPalette.ColorRole.Base)
            is_dark = bg_color.lightness() < 128
        except Exception:
            is_dark = False
        self._hist_list_widget.set_theme(is_dark)
        self._hist_list_widget.show()
        size = self._hist_list_widget.size()
        point = self.rect().topRight() - QtCore.QPoint(size.width(), size.height())
        self._hist_list_widget.move(self.mapToGlobal(point))
        self._hist_list_widget._filter._filter_line.setFocus()

class QHistoryListModel(QtCore.QAbstractListModel):
    def __init__(self, history: list[str], parent: QHistoryList):
        super().__init__(parent)
        self._history = history
        self.set_theme(False)  # initialize brushes
    
    def set_theme(self, is_dark: bool):
        if is_dark:
            self._brush_even = QtGui.QBrush(QtGui.QColor(23, 23, 0))
            self._brush_odd = QtGui.QBrush(QtGui.QColor(0, 0, 0))
            self._brush_current = QtGui.QBrush(QtGui.QColor(17, 17, 17))
        else:
            self._brush_current = QtGui.QBrush(QtGui.QColor(232, 232, 255))
            self._brush_even = QtGui.QBrush(QtGui.QColor(255, 255, 255))
            self._brush_odd = QtGui.QBrush(QtGui.QColor(238, 238, 238))

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
                return self._brush_current
            if index.row() % 2 == 0:
                return self._brush_even
            else:
                return self._brush_odd
        return None
    
    if TYPE_CHECKING:
        def parent(self) -> QHistoryList:
            return super().parent()

class QHistoryWidget(QtW.QWidget):
    """Widget that will be shown when the user clicks on the history button."""
    def __init__(self, btn: QShowHistoryButton):
        super().__init__()
        _layout = QtW.QVBoxLayout(self)
        
        self._filter = QHistoryFilter()
        self._history_list = QHistoryList(btn)
        self._insert_btn = QtW.QPushButton("Insert")
        self._insert_btn.setToolTip("Insert selected commands into the command line")
        self._insert_btn.setFixedWidth(80)
        self._insert_btn.clicked.connect(self._insert_btn_clicked)
        
        self._copy_btn = QtW.QPushButton("Copy")
        self._copy_btn.setToolTip("Copy selected commands to clipboard")
        self._copy_btn.setFixedWidth(80)
        self._copy_btn.clicked.connect(self._copy_btn_clicked)
        
        self._save_btn = QtW.QPushButton("Save ...")
        self._save_btn.setToolTip("Save selected commands to a file")
        self._save_btn.setFixedWidth(80)
        self._save_btn.clicked.connect(self._save_btn_clicked)
        _footer = QtW.QHBoxLayout()
        _footer.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        _footer.setContentsMargins(0, 0, 0, 0)
        _footer.addWidget(self._insert_btn)
        _footer.addWidget(self._copy_btn)
        _footer.addWidget(self._save_btn)
        self._is_dark = False
        _layout.addWidget(self._filter)
        _layout.addWidget(self._history_list)
        _layout.addLayout(_footer)
        
        self.setMaximumHeight(500)
        self._filter._filter_line.textChanged.connect(self._filter_text_changed)

    def _filter_text_changed(self, txt: str):
        if txt == "":
            self._history_list.set_list(HistoryManager.instance().aslist())
        texts = self._filter.run_filter(self._history_list._model._history)
        self._history_list.set_list(texts)
    
    def _selection_to_text(self) -> str:
        """Get the selected text from the history list."""
        selected = self._history_list.selectedIndexes()
        if not selected:
            return ""
        texts = [index.data(QtCore.Qt.ItemDataRole.DisplayRole) for index in selected]
        return "\n".join(texts)
    
    def _cli_widget(self) -> "QCommandLineEdit":
        return self._history_list._btn._cli_widget

    def _insert_btn_clicked(self):
        """Insert the selected text into the command line."""
        if text := self._selection_to_text():
            cli_widget = self._cli_widget()
            cli_widget.setText(text)
            self.hide()
            cursor = cli_widget.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            cli_widget.setTextCursor(cursor)
            self.hide()
            cli_widget.setFocus()
    
    def _copy_btn_clicked(self):
        """Copy the selected text to the clipboard."""
        if text := self._selection_to_text():
            clipboard = QtW.QApplication.clipboard()
            clipboard.setText(text)

    def _save_btn_clicked(self):
        """Save the selected text to a file."""
        if text := self._selection_to_text():
            file_name, _ = QtW.QFileDialog.getSaveFileName(
                self._cli_widget(),
                "Save File",
                "", 
                "ChimeraX commands (*.cxc);;All Files (*)",
            )
            if file_name:
                Path(file_name).write_text(text)

    def set_theme(self, is_dark: bool):
        self._history_list._model.set_theme(is_dark)
        self._is_dark = is_dark

class QHistoryList(QtW.QListView):
    def __init__(self, parent: QShowHistoryButton) -> None:
        super().__init__(parent)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._btn = parent
        self.set_list(HistoryManager.instance().aslist())

    def set_list(self, hist: list[str]):
        self._model = QHistoryListModel(hist, self)
        self.setModel(self._model)
        self.scrollToBottom()
        self.setCurrentIndex(self._model.index(self._model.rowCount() - 1, 0))
        if list_widget := self._btn._hist_list_widget:
            list_widget.set_theme(list_widget._is_dark)

class QFilterLineEdit(QtW.QLineEdit):
    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        if a0.key() in (
            QtCore.Qt.Key.Key_Up,
            QtCore.Qt.Key.Key_Down,
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.Key.Key_PageDown,
            QtCore.Qt.Key.Key_PageUp
        ):
            self._history_widget()._history_list.keyPressEvent(a0)
            return None
        return super().keyPressEvent(a0)
    
    def _history_widget(self) -> QHistoryWidget:
        return self.parentWidget().parentWidget()
    
class QHistoryFilter(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QtW.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        
        self._filter_line = QFilterLineEdit()
        
        self._method_choice = QtW.QComboBox()

        self._method_choice.addItems(["abc___", "___abc", "__abc__", ".*"])
        self._method_choice.setItemData(0, "Starts with", QtCore.Qt.ItemDataRole.ToolTipRole)
        self._method_choice.setItemData(1, "Ends with", QtCore.Qt.ItemDataRole.ToolTipRole)
        self._method_choice.setItemData(2, "Contains", QtCore.Qt.ItemDataRole.ToolTipRole)
        self._method_choice.setItemData(3, "Regular expression match", QtCore.Qt.ItemDataRole.ToolTipRole)

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
        elif self._method_choice.currentIndex() == 3:
            out = [text for text in texts if re.match(self._filter_line.text(), text) is not None]
        else:
            out = texts
        return out
