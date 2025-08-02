from __future__ import annotations

from qtpy import QtWidgets as QtW
from typing import Iterator
from ..algorithms.action import CommandPaletteAction

def command_palette_actions(main_window: QtW.QMainWindow) -> list[CommandPaletteAction]:
    # Add menu actions
    actions = []
    for child in main_window.menuBar().children():
        if not isinstance(child, QtW.QMenu):
            continue
        group_name = child.title().replace("&", "")
        if group_name == "":
            continue
        group_name = child.title().replace("&", "")
        for action, context in iter_actions(child):
            ca = CommandPaletteAction(
                make_command(action),
                desc=" > ".join([group_name, *context, action.text()]).replace("&", ""),
                tooltip=action.toolTip(),
            )
            actions.append(ca)
    # Add toolbar actions
    for action, context in iter_toolbar_actions(main_window):
        ca = CommandPaletteAction(
            make_command(action), 
            desc=" > ".join(["Toolbar", *context]),
            tooltip=action.toolTip(),
        )
        actions.append(ca)
    return actions


def iter_actions(menu: QtW.QMenu, cur=None) -> Iterator[tuple[QtW.QAction, list[str]]]:
    cur = cur or []
    for ac in menu.actions():
        parent = ac.parent()
        if parent is menu:
            continue
        if isinstance(parent, QtW.QMenu):
            yield from iter_actions(ac.parent(), cur=[*cur, ac.text()])
        else:
            yield ac, cur

def make_command(action: QtW.QAction):
    return lambda: action.trigger()

def iter_toolbar_actions(
    main_window: QtW.QMainWindow,
) -> Iterator[tuple[QtW.QAction, list[str]]]:
    
    tabbed = _find_tabbed_toolbar(main_window)
    for i in range(tabbed.count()):
        tab_name = tabbed.tabText(i)
        toolbar = tabbed.widget(i)
        for child in toolbar.children():
            if type(child) is QtW.QWidget:
                label_widget = _find_label_widget(child)
                if label_widget is None:
                    for action in _iter_toolbutton_action(child):
                        text = action.text().replace("\n", " ")
                        yield action, [tab_name, text]
                else:
                    label = label_widget.text()
                    for action in _iter_toolbutton_action(child):
                        text = action.text().replace("\n", " ")
                        yield action, [tab_name, label, text]

def _find_tabbed_toolbar(main_window: QtW.QMainWindow) -> QtW.QTabWidget:
    """Find the TabbedToolBar in the ChimeraX main window"""
    tb: QtW.QWidget | None = None
    for c in main_window.children():
        if isinstance(c, QtW.QDockWidget):
            if c.windowTitle() == "Toolbar":
                tb = c.widget()
                break
    if tb is None:
        raise ValueError("Toolbar not found")
    ttb = tb.children()[1].children()[0]
    
    if not isinstance(ttb, QtW.QTabWidget):
        raise ValueError("Tabbed toolbar not found")
    return ttb

def _find_label_widget(widget: QtW.QWidget) -> QtW.QLabel | None:
    """Find the label widget in a section widget."""
    children = widget.children()
    for child in children:
        if isinstance(child, QtW.QLabel):
            return child
    return None

def _iter_toolbutton_action(widget: QtW.QWidget):
    for child in widget.children():
        if isinstance(child, QtW.QToolButton):
            actions = child.actions()
            if len(actions) > 0:
                yield actions[0]
