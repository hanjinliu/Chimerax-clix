from ..widgets import QCommandLineEdit
from .._types import Mode
from qtpy import QtWidgets as QtW, QtCore

from .._preference import load_preference

class Session:
    """Mock session for testing purposes."""
    def __init__(self):
        self.ui = UI()

class QSingleWidget(QtW.QWidget):
    def __init__(self, widget: QtW.QWidget):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

class UI:
    def __init__(self):
        self.main_window = QtW.QMainWindow()
        dock = QtW.QDockWidget("Toolbar")
        tabbed = QtW.QTabWidget()
        w0 = QSingleWidget(QSingleWidget(tabbed))
        toolbar = QtW.QToolBar()
        tabbed.addTab(toolbar, "Tab1")
        dock.setWidget(w0)
        self.main_window.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, dock)

def _get_widget():
    return QCommandLineEdit({}, Session(), load_preference())

def test_widget_construction(qtbot):
    widget = _get_widget()
    qtbot.addWidget(widget)
    widget.show()
    widget.insertPlainText("a")
    widget.insertPlainText("b")
    widget.insertPlainText(" ")

def test_switching_mode(qtbot):
    widget = _get_widget()
    qtbot.addWidget(widget)
    widget.show()
    assert widget._mode is Mode.CLI
    widget.insertPlainText(">")
    assert widget._mode is Mode.PALETTE
    widget.clear()
    assert widget._mode is Mode.CLI
    widget.insertPlainText("/")
    assert widget._mode is Mode.RECENT
