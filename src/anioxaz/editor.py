from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Markdown,
    RichLog,
    Static,
    TextArea,
)

from .core import APP_NAME


@dataclass
class Buffer:
    text: str = ""
    path: Optional[Path] = None
    dirty: bool = False
    language: str = "python"

    @property
    def name(self) -> str:
        return self.path.name if self.path else "Untitled"

    @property
    def label(self) -> str:
        return self.name + (" ●" if self.dirty else "")


class PromptScreen(ModalScreen[Optional[str]]):
    """Reusable large prompt for build, fix, generate, shell, and philosophy."""

    BINDINGS = [
        Binding("ctrl+enter", "submit", "Submit"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        title: str,
        hint: str,
        initial: str = "",
        submit_label: str = "Submit",
    ) -> None:
        super().__init__()
        self.title = title
        self.hint = hint
        self.initial = initial
        self.submit_label = submit_label

    def compose(self):
        with Container(classes="modal_panel prompt_modal"):
            yield Static(self.title, classes="modal_title")
            yield Static(self.hint, classes="modal_hint")
            yield TextArea(
                self.initial,
                id="prompt_input",
                soft_wrap=True,
                show_line_numbers=False,
            )
            with Horizontal(classes="modal_actions"):
                yield Button(self.submit_label, id="submit", variant="primary")
                yield Button("Cancel", id="cancel")
            yield Static(
                "Enter newline · Ctrl+Enter submit · ESC cancel",
                classes="key_hint",
            )

    def on_mount(self) -> None:
        self.query_one("#prompt_input", TextArea).focus()

    def action_submit(self) -> None:
        value = self.query_one("#prompt_input", TextArea).text
        if not value.strip():
            self.app.notify("Write something first.", severity="warning")
            return
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.action_submit()
        elif event.button.id == "cancel":
            self.action_cancel()


class ShortPromptScreen(ModalScreen[Optional[str]]):
    """Single-line prompt for short values such as a path or line number."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, placeholder: str, initial: str = "") -> None:
        super().__init__()
        self.title = title
        self.placeholder = placeholder
        self.initial = initial

    def compose(self):
        with Container(classes="modal_panel short_modal"):
            yield Static(self.title, classes="modal_title")
            yield Input(self.initial, placeholder=self.placeholder, id="short_input")
            with Horizontal(classes="modal_actions"):
                yield Button("Continue", id="submit", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#short_input", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.dismiss(self.query_one("#short_input", Input).value.strip() or None)
        elif event.button.id == "cancel":
            self.dismiss(None)


class ChoiceScreen(ModalScreen[Optional[str]]):
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def __init__(self, title: str, choices: Iterable[tuple[str, str]]) -> None:
        super().__init__()
        self.title = title
        self.choices = list(choices)

    def compose(self):
        with Container(classes="modal_panel choice_modal"):
            yield Static(self.title, classes="modal_title")
            for choice_id, label in self.choices:
                yield Button(label, id=choice_id, classes="choice_button")
            yield Button("Back", id="cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None if event.button.id == "cancel" else event.button.id)


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, message: str, confirm_label: str = "Confirm") -> None:
        super().__init__()
        self.title = title
        self.message = message
        self.confirm_label = confirm_label

    def compose(self):
        with Container(classes="modal_panel confirm_modal"):
            yield Static(self.title, classes="modal_title")
            yield Static(self.message, classes="modal_hint")
            with Horizontal(classes="modal_actions"):
                yield Button(self.confirm_label, id="confirm", variant="error")
                yield Button("Cancel", id="cancel")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class FindReplaceScreen(ModalScreen[Optional[tuple[str, str, bool]]]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, current_find: str = "") -> None:
        super().__init__()
        self.current_find = current_find

    def compose(self):
        with Container(classes="modal_panel replace_modal"):
            yield Static("REPLACE", classes="modal_title")
            yield Input(self.current_find, placeholder="Find", id="find_input")
            yield Input(placeholder="Replace with", id="replace_input")
            yield Checkbox("Case sensitive", id="case_sensitive")
            with Horizontal(classes="modal_actions"):
                yield Button("Review replace all", id="submit", variant="primary")
                yield Button("Cancel", id="cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        needle = self.query_one("#find_input", Input).value
        if not needle:
            self.app.notify("Enter text to find.", severity="warning")
            return
        replacement = self.query_one("#replace_input", Input).value
        case_sensitive = self.query_one("#case_sensitive", Checkbox).value
        self.dismiss((needle, replacement, case_sensitive))


class HelpScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close")]

    def compose(self):
        help_text = """# ANIOXAZ help

**Main menu:** arrows navigate · Enter selects · Tab opens the editor.

**Prompt:** Enter adds a line · Ctrl+Enter submits · Escape cancels.

**Editor:** Escape returns · Ctrl+S saves · Ctrl+O opens · Ctrl+Shift+S saves
as · Alt+N creates a buffer · Ctrl+W closes a buffer · Ctrl+Page Up/Down
switches buffers · Ctrl+F searches · F3 and Shift+F3 cycle matches · Ctrl+H
replaces · Ctrl+G goes to a line · Ctrl+K and Ctrl+U cut/paste a line ·
Ctrl+Shift+K deletes a line · Alt+Z toggles wrapping.

TextArea supplies normal selection, clipboard, undo/redo, navigation, page
scrolling, indentation, and bracket matching. The Architect plans and
explains. The Coder writes code only. With only Coder loaded, build requests
use clearly labeled fallback mode. Philosophy Files are sent only to Architect."""
        with Container(classes="modal_panel help_modal"):
            yield Markdown(help_text)
            yield Button("Close", id="close", variant="primary")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class PhilosophyViewScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close")]

    def __init__(self, content: str, path: Optional[Path]) -> None:
        super().__init__()
        self.content = content
        self.path = path

    def compose(self):
        title = self.path.name if self.path else "session only"
        with Container(classes="modal_panel philosophy_view"):
            yield Static("PHILOSOPHY · " + title, classes="modal_title")
            yield Markdown(self.content)
            yield Button("Close", id="close", variant="primary")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class EditorScreen(Screen[None]):
    """Nano-style editing surface; TextArea handles ordinary code editing."""

    BINDINGS = [
        Binding("escape", "back_to_menu", "Menu"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+o", "open_file", "Open"),
        Binding("ctrl+shift+s", "save_as", "Save As"),
        Binding("alt+n", "new_buffer", "New"),
        Binding("ctrl+w", "close_buffer", "Close"),
        Binding("ctrl+pageup", "previous_buffer", "Previous tab"),
        Binding("ctrl+pagedown", "next_buffer", "Next tab"),
        Binding("ctrl+f", "find", "Find"),
        Binding("f3", "find_next", "Next"),
        Binding("shift+f3", "find_previous", "Previous"),
        Binding("ctrl+h", "replace", "Replace"),
        Binding("ctrl+g", "go_to_line", "Go to line"),
        Binding("ctrl+k", "cut_line", "Cut line"),
        Binding("ctrl+u", "paste_line", "Paste line"),
        Binding("ctrl+shift+k", "delete_line", "Delete line"),
        Binding("alt+z", "toggle_wrap", "Wrap"),
        Binding("alt+1", "buffer_1", show=False),
        Binding("alt+2", "buffer_2", show=False),
        Binding("alt+3", "buffer_3", show=False),
        Binding("alt+4", "buffer_4", show=False),
        Binding("alt+5", "buffer_5", show=False),
        Binding("alt+6", "buffer_6", show=False),
        Binding("alt+7", "buffer_7", show=False),
        Binding("alt+8", "buffer_8", show=False),
        Binding("alt+9", "buffer_9", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.loading_buffer = False

    def compose(self):
        yield Static("ANIOXAZ · EDITOR", id="compact_header")
        with Container(id="editor_panel", classes="panel"):
            yield Static("EDITOR", classes="panel_heading")
            yield Static("", id="tab_strip", classes="tab_strip")
            yield TextArea(
                "",
                id="editor",
                language="python",
                soft_wrap=True,
                show_line_numbers=True,
            )
        with Container(id="editor_output_panel", classes="panel"):
            yield Static("OUTPUT", classes="panel_heading")
            yield RichLog(id="editor_output", wrap=True, markup=False, highlight=False)
        yield Static("", id="editor_status", classes="status_text status_idle")
        yield Static(
            "ESC menu · Ctrl+S save · Ctrl+F search · Ctrl+PageUp/Down tabs",
            id="editor_hint",
            classes="hint_text",
        )

    def on_mount(self) -> None:
        self.refresh_from_buffer()
        self.app.render_history(self.query_one("#editor_output", RichLog))
        self.query_one("#editor", TextArea).focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "editor" and not self.loading_buffer:
            self.app.update_active_buffer(event.text_area.text)
            self.refresh_status()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        if event.text_area.id == "editor":
            self.refresh_status()

    def refresh_from_buffer(self) -> None:
        buffer = self.app.active_buffer
        editor = self.query_one("#editor", TextArea)
        self.loading_buffer = True
        editor.text = buffer.text
        editor.language = buffer.language
        editor.soft_wrap = self.app.word_wrap
        self.loading_buffer = False
        self.query_one("#tab_strip", Static).update(self.app.tab_strip_text())
        self.refresh_status()

    def refresh_status(self) -> None:
        buffer = self.app.active_buffer
        row, column = self.query_one("#editor", TextArea).cursor_location
        dirty = " · ● unsaved" if buffer.dirty else ""
        self.query_one("#editor_status", Static).update(
            f"Editing · {buffer.name}{dirty} · {buffer.language} · "
            f"Ln {row + 1}, Col {column + 1} · {self.app.model_summary()}"
        )

    def action_back_to_menu(self) -> None:
        self.app.leave_editor()

    def action_save(self) -> None:
        self.app.save_active()

    def action_open_file(self) -> None:
        self.app.ask_open_file()

    def action_save_as(self) -> None:
        self.app.ask_save_as()

    def action_new_buffer(self) -> None:
        self.app.new_buffer()

    def action_close_buffer(self) -> None:
        self.app.close_active_buffer()

    def action_previous_buffer(self) -> None:
        self.app.switch_buffer(-1)

    def action_next_buffer(self) -> None:
        self.app.switch_buffer(1)

    def action_find(self) -> None:
        self.app.ask_find()

    def action_find_next(self) -> None:
        self.app.find_next(False)

    def action_find_previous(self) -> None:
        self.app.find_next(True)

    def action_replace(self) -> None:
        self.app.ask_replace()

    def action_go_to_line(self) -> None:
        self.app.ask_go_to_line()

    def action_cut_line(self) -> None:
        self.app.cut_current_line()

    def action_paste_line(self) -> None:
        self.app.paste_line()

    def action_delete_line(self) -> None:
        self.app.delete_current_line()

    def action_toggle_wrap(self) -> None:
        self.app.toggle_word_wrap()

    def _switch_to(self, index: int) -> None:
        self.app.switch_to_buffer(index)

    def action_buffer_1(self) -> None:
        self._switch_to(0)

    def action_buffer_2(self) -> None:
        self._switch_to(1)

    def action_buffer_3(self) -> None:
        self._switch_to(2)

    def action_buffer_4(self) -> None:
        self._switch_to(3)

    def action_buffer_5(self) -> None:
        self._switch_to(4)

    def action_buffer_6(self) -> None:
        self._switch_to(5)

    def action_buffer_7(self) -> None:
        self._switch_to(6)

    def action_buffer_8(self) -> None:
        self._switch_to(7)

    def action_buffer_9(self) -> None:
        self._switch_to(8)
