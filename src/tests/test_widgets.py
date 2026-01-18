from ..widgets import QCommandLineEdit

def test_widget_construction(qtbot):
    widget = QCommandLineEdit({}, None, None)
    qtbot.addWidget(widget)
