from __future__ import annotations
from typing import Iterable
from qtpy import QtCore, QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal
from .._utils import rgba_to_html

# modified from napari/_qt/widgets/qt_color_swatch.py
class QColorSwatch(QtW.QFrame):
    colorChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self.colorChanged.connect(self._update_swatch_style)
        self.setFixedWidth(40)
        self._pressed_pos = None
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tooltip = lambda: rgba_to_html(self.getQColor().getRgbF())

    def heightForWidth(self, w: int) -> int:
        return int(w * 0.667)

    def _update_swatch_style(self, _=None) -> None:
        rgba = f'rgba({",".join(str(int(x*255)) for x in self._color)})'
        self.setStyleSheet("QColorSwatch {background-color: " + rgba + ";}")

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._pressed_pos = self.mapToGlobal(a0.pos())
        return super().mousePressEvent(a0)

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        # moved?
        if self._pressed_pos is not None:
            pos = self.mapToGlobal(a0.pos())
            dx = self._pressed_pos.x() - pos.x()
            dy = self._pressed_pos.y() - pos.y()
            if dx**2 + dy**2 > 4:
                self._pressed_pos = None
        return super().mouseMoveEvent(a0)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Show QColorPopup picker when the user clicks on the swatch."""
        # inside the widget?
        if self._pressed_pos is None or not self.rect().contains(event.pos()):
            return None
        if event.button() == Qt.MouseButton.LeftButton:
            initial = self.getQColor()
            dlg = QtW.QColorDialog(initial, self)
            dlg.setOptions(QtW.QColorDialog.ColorDialogOption.ShowAlphaChannel)
            ok = dlg.exec_()
            if ok:
                self.setColor(dlg.selectedColor())
        self._pressed_pos = None

    def getQColor(self) -> QtGui.QColor:
        return QtGui.QColor.fromRgbF(*self._color)

    def setColor(self, color: QtGui.QColor) -> None:
        old_color = rgba_to_html(self._color)
        self._color = QtGui.QColor.getRgbF(color)
        if rgba_to_html(self._color) != old_color:
            self.colorChanged.emit()

    def event(self, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.ToolTip:
            assert isinstance(event, QtGui.QHelpEvent)
            QtW.QToolTip.showText(event.globalPos(), self._tooltip(), self)
            return True
        return super().event(event)

class QLabeledColorSwatch(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        self._label = QtW.QLabel()
        layout.addWidget(self._label)
        self._swatch = QColorSwatch()
        layout.addWidget(self._swatch, alignment=Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(0, 0, 0, 0)
    
    def setLabel(self, label: str) -> None:
        self._label.setText(label)
    
    def setColor(self, color: QtGui.QColor) -> None:
        self._swatch.setColor(color)
    
    def getColor(self) -> QtGui.QColor:
        return self._swatch.getQColor()
