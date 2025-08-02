from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Iterator
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
from html import escape

from .consts import TOOLTIP_FOR_AMINO_ACID
from ._base import QSelectablePopup, ItemContent, is_too_bottom
from .._history import HistoryManager
from ..types import WordInfo, resolve_cmd_desc, FileSpec
from ..algorithms.action import CommandPaletteAction, RecentFileAction
from ..palette import command_palette_actions, color_text_by_match
from .._preference import load_preference
from .._utils import colored
from ..algorithms import complete_path, complete_keyword_name_or_value, CompletionState

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
        if comp := self.current_item_content():
            self.complete_with(comp.text, comp.type)
            comp.action.execute(self.parentWidget())

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
    
    def _selection_changed(self, idx: int, content: ItemContent):
        """Callback of the change in the current list widget index."""
        if not self.isVisible():
            return
        text = content.text
        parent = self.parentWidget()
        tooltip_widget = parent._tooltip_widget
        if parent._current_completion_state.type in ("residue", "model,residue"):
            # set residue name
            tooltip = TOOLTIP_FOR_AMINO_ACID.get(text.split(":")[-1], "")
            if tooltip:
                tooltip_widget.setText(tooltip)
                # adjust the height of the tooltip
                metrics = QtGui.QFontMetrics(tooltip_widget.font())
                height = min(280, metrics.height() * (tooltip.count("\n") + 1) + 6)
                tooltip_widget.setFixedHeight(height)
                # move the tooltip
                self._try_show_tooltip_widget()
        elif parent._current_completion_state.type in ("keyword", "selector"):
            pass
        elif winfo := parent._commands.get(text, None):
            parent._adjust_tooltip_for_list(idx)
            tooltip_widget.setWordInfo(winfo, text)
            self._try_show_tooltip_widget()

    def _try_show_tooltip_widget(self):
        parent = self.parentWidget()
        tooltip_widget = parent._tooltip_widget
        tooltip_widget.setFixedWidth(360)
        tooltip = tooltip_widget.toPlainText()
        if (
            not tooltip_widget.isVisible()
            and tooltip != ""
            and "path" not in parent._current_completion_state.type.split(",")
        ):
            # show tooltip because there's something to show
            tooltip_widget.show()
            parent.setFocus()
        elif tooltip == "":
            tooltip_widget.hide()
        
        if tooltip_widget.isVisible():
            if self.isVisible():
                # show next to the cursor
                parent._adjust_tooltip_for_list(self.currentRow())
            else:
                # show beside the completion list
                _height = tooltip_widget.height()
                pos = parent.mapToGlobal(parent.cursorRect().bottomRight())
                if is_too_bottom(pos.y() + _height):
                    top_right = parent.mapToGlobal(parent.cursorRect().topRight())
                    height_vector = QtCore.QPoint(0, _height)
                    pos = top_right - height_vector
                tooltip_widget.move(pos)
        return None

    def _get_completion_list(self, text: str) -> CompletionState:
        if text == "" or text.startswith("#"):
            return CompletionState(text, [], type="empty-text")

        # command completion
        current_command, matched_commands = self._current_and_matched_commands(text)
        if len(matched_commands) > 0:
            if len(matched_commands) == 1 and matched_commands[0] == text.strip():
                # not need to show the completion list
                pass
            elif " " not in text:
                # if `matched_commands` is
                #   toolshed list
                #   toolshed install
                # then `all_commands` is
                #   toolshed
                #   toolshed list
                #   toolshed install
                all_commands: dict[str, None] = {}  # ordered set
                for cmd in matched_commands:
                    all_commands[cmd.split(" ")[0]] = None
                for cmd in matched_commands:
                    all_commands[cmd] = None
                matched_commands = list(all_commands.keys())
            return CompletionState(text, matched_commands, current_command, type="command")
    
        # attribute completion
        *pref, last_word = text.rsplit(" ")
        if pref == []:
            return CompletionState(text, [], current_command)

        cmd = current_command or self.parentWidget()._current_completion_state.command or ""
        args = pref[cmd.count(" ") + 1:]
        if winfo := self.parentWidget()._commands.get(cmd, None):
            # command keyword name/value completion
            if state := complete_keyword_name_or_value(
                args=args,
                last_word=last_word,
                current_command=current_command,
                text=text,
                context=self.parentWidget().get_context(winfo),
            ):
                # TODO: don't show keywords that are already in the command line
                return state

        # path completion
        if state := complete_path(last_word, current_command):
            return state

        return CompletionState(text, [], current_command)
   
    def _current_and_matched_commands(self, text: str) -> tuple[str, list[str]]:
        matched_commands: list[str] = []
        current_command: str | None = None
        text_lstrip = text.lstrip()
        text_strip = text.strip()
        for command_name in self.parentWidget()._commands.keys():
            if command_name.startswith(text_lstrip):
                # if `text` is "toolshed", add
                #   toolshed list
                #   toolshed install ...
                # to `matched_commands`
                matched_commands.append(command_name)
            elif text_strip == command_name or text_strip.startswith(command_name.rstrip() + " "):
                current_command = command_name
        return current_command, matched_commands


    def try_show_me(self):
        parent = self.parentWidget()
        parent._update_completion_state(allow_auto=False)
        items = parent._current_completion_state.completions

        # if nothing to show, do not show the list
        if len(items) == 0:
            self.hide()
            return
        
        # if the next character exists and is not a space, do not show the list
        _cursor = parent.textCursor()
        if not _cursor.atEnd():
            _cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.Right,
                QtGui.QTextCursor.MoveMode.KeepAnchor
            )
            if not _cursor.selectedText().isspace():
                self.hide()
                return
        
        self.add_items_with_highlight(parent._current_completion_state)
        parent._optimize_selectable_popup_geometry(self)
        return None
    
    def post_show_me(self):
        if self.isVisible():
            self.setCurrentRow(0)

        parent = self.parentWidget()
        # if needed, show/hide the tooltip widget
        if parent._current_completion_state.command is None:
            if parent._tooltip_widget.isVisible():
                parent._tooltip_widget.hide()
        elif parent._current_completion_state.type in ("residue", "model,residue"):
            self._try_show_tooltip_widget()    
        else:
            name = parent._current_completion_state.command
            cmd = parent._commands[name]
            parent._tooltip_widget.setWordInfo(cmd, name)
            self._try_show_tooltip_widget()
    
        if self.count() > 0:
            self.set_row(parent._current_completion_state.index_start)

        # one-line suggestion
        if not parent._dont_need_inline_suggestion:
            this_line = parent.textCursor().block().text()
            if this_line.startswith("#"):
                # comment line does not need suggestion
                return None
            if suggested := HistoryManager.instance().suggest(this_line):
                parent._show_inline_suggestion(suggested)


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
            item, current_label = self.prep_item(row, count_before)
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
            score = self._match_score(command.desc, input_text)
            if score > 0.0:
                commands.append((score, command))
        commands.sort(key=lambda x: x[0], reverse=True)
        for _, command in commands:
            yield command

    def exec_current_item(self):
        if comp := self.current_item_content():
            self.parentWidget()._close_popups()
            comp.action.execute(self.parentWidget())

    @cache
    def get_all_commands(self) -> list[CommandPaletteAction]:
        return command_palette_actions(self.session().ui.main_window)

    def _match_score(self, command_text: str, input_text: str) -> float:
        """Return a match score (between 0 and 1) for the input text."""
        name = command_text.lower()
        if all(word in name for word in input_text.lower().split(" ")):
            return 1.0
        if len(input_text) < 4 and all(char in name for char in input_text.lower()):
            return 0.7
        return 0.0


class QRecentFilePopup(QSelectablePopup):
    def exec_current_item(self):
        self.parentWidget()._close_popups()
        if content := self.current_item_content():
            content.action.execute(self.parentWidget())
    
    def add_items_with_highlight(self, cmp: CompletionState) -> None:
        match_color = load_preference().color_theme.matched
        count_before = self.count()
        row = 0
        for row, spec in enumerate(self.iter_matched_files(cmp.text)):
            item, current_label = self.prep_item(row, count_before)
            item.setData(
                Qt.ItemDataRole.UserRole,
                ItemContent(spec.path, "", RecentFileAction(spec), "file"),
            )
            file_path = Path(spec.path)
            label_txt_path = file_path.parent / color_text_by_match(
                cmp.text, file_path.name, match_color
            )
            current_label.setText(label_txt_path.as_posix())
            row = row + 1
        
        for _ in range(row, count_before):
            self.takeItem(row)
    
    def _selection_changed(self, idx: int, content: ItemContent):
        parent = self.parentWidget()
        tooltip_widget = parent._tooltip_widget
        action = content.action
        if isinstance(action, RecentFileAction):
            tooltip_widget.setBase64Image(action.fs.image)
    
    def _try_show_tooltip_widget(self):
        parent = self.parentWidget()
        if self.count() > 0:
            parent._tooltip_widget.show()
        else:
            parent._tooltip_widget.hide()
        if self.isVisible():
            # show next to the cursor
            parent._adjust_tooltip_for_list(self.currentRow())

    def iter_matched_files(self, input_text: str) -> Iterator[FileSpec]:
        ctx = self.parentWidget().get_context(None)
        files = ctx.get_file_list()
        input_text = input_text.strip().lower()
        if input_text == "":
            yield from files[::-1]
        else:
            for file in reversed(files):
                if input_text in Path(file.path).name.lower():
                    yield file

    def post_show_me(self):
        parent = self.parentWidget()
        if content := self.current_item_content():
            if isinstance(action := content.action, RecentFileAction):
                self._try_show_tooltip_widget()
                parent._tooltip_widget.setBase64Image(action.fs.image)
        
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
                f"<b>{name}</b>: {self._type_to_name(typ, color_theme.type)}"
            )
        # here, some arguments are both optional and keyword
        keywords = cmd_desc._keyword.copy()
        for name, typ in cmd_desc._optional.items():
            annot = self._type_to_name(typ, color_theme.type)
            if name in keywords:
                strings.append(f"<b>{name}</b>: {annot} <i>(optional, keyword)</i>")
                keywords.pop(name)
            else:
                strings.append(f"<b>{name}</b>: {annot} <i>(optional)</i>")
        for name, typ in keywords.items():
            strings.append(
                f"<b>{name}</b>: {self._type_to_name(typ, color_theme.type)} "
                "<i>(keyword)</i>"
            )
        self.setText("<br>".join(strings))
        return None
    
    def setBase64Image(self, base64_image: str):
        self.setHtml(f'<img src="data:image/png;base64,{base64_image}">')
        size = self.document().size()
        length = int(min(size.width(), size.height(), 300)) + 12
        self.setFixedSize(length, length)

    def _type_to_name(self, typ, color):
        return colored(escape(typ.name), color)
