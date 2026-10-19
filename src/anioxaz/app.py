from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Label, ListItem, ListView, LoadingIndicator, RichLog, Static

from .core import APP_NAME, DEFAULT_ITERATION_CAP, MAX_LOG_LINES, detect_language
from .editor import (
    Buffer,
    ChoiceScreen,
    ConfirmScreen,
    EditorScreen,
    FindReplaceScreen,
    HelpScreen,
    PhilosophyViewScreen,
    PromptScreen,
    ShortPromptScreen,
)
from .executor import CodeExecutor, Terminal
from .models import Architect, Coder


class AnioxazApp(App[None]):
    """The ANIOXAZ Textual app."""

    TITLE = APP_NAME
    SUB_TITLE = "offline · local · yours"
    CSS = """
    Screen {
        background: #0f172a;
        color: #e2e8f0;
    }

    #brand {
        height: 3;
        content-align: center middle;
        color: #7dd3fc;
        text-style: bold;
    }

    #main_panels {
        height: 1fr;
        width: 100%;
    }

    #menu_panel, #output_panel, .panel {
        border: round #334155;
        padding: 1 2;
        margin: 0 1 0 0;
    }

    #menu_panel {
        width: 26;
    }

    #output_panel {
        width: 1fr;
    }

    #status_bar {
        height: 3;
        margin-top: 1;
    }

    .status_text {
        width: 1fr;
        padding: 0 1;
        content-align: left middle;
    }

    .status_idle { color: #94a3b8; }
    .status_thinking { color: #fbbf24; }
    .status_running { color: #34d399; }
    .status_error { color: #f87171; }

    .hint_text {
        color: #94a3b8;
        height: 1;
        margin-top: 0;
    }

    .modal_panel {
        width: 70;
        height: auto;
        max-height: 80vh;
        background: #111827;
        border: heavy #60a5fa;
        padding: 1 2;
    }

    .modal_title {
        color: #7dd3fc;
        text-style: bold;
        margin-bottom: 1;
    }

    .modal_hint {
        color: #cbd5e1;
        margin-bottom: 1;
    }

    .key_hint {
        color: #94a3b8;
        margin-top: 1;
    }

    .activity {
        width: 3;
        color: #7dd3fc;
    }
    """

    BINDINGS = [
        Binding("tab", "open_editor", "Editor"),
        Binding("ctrl+q", "quit_app", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.architect = Architect("architect")
        self.coder = Coder("coder")
        self.philosophy_text = ""
        self.philosophy_path: Optional[Path] = None
        self.iteration_cap = DEFAULT_ITERATION_CAP
        self.auto_heal = False
        self.pipeline_active = False
        self.word_wrap = True
        self.buffers = [Buffer()]
        self.active_buffer_index = 0
        self.internal_line_clipboard = ""
        self.search_term = ""
        self.search_offset = -1
        self.status_mode = "idle"
        self.status_message = "Ready"
        self.output_history = [
            "Welcome to ANIOXAZ.",
            "Load Architect and Coder models from Model for the full pipeline.",
        ]
        self.terminal = Terminal(self.thread_log)
        self.executor = CodeExecutor(self.trace_event_from_worker)

    @property
    def active_buffer(self) -> Buffer:
        return self.buffers[self.active_buffer_index]

    def compose(self) -> ComposeResult:
        yield Static("[b]ANIOXAZ[/b]\n[dim]offline · local · yours[/dim]", id="brand", markup=True)
        with Horizontal(id="main_panels"):
            with Container(id="menu_panel", classes="panel"):
                yield Static("MENU", classes="panel_heading")
                yield ListView(
                    *[
                        ListItem(Label(label), id=action)
                        for label, action in (
                            ("▶ Editor", "editor"),
                            ("▶ Build", "build"),
                            ("▶ Run", "run"),
                            ("▶ Explain", "explain"),
                            ("▶ Fix", "fix"),
                            ("▶ Generate", "generate"),
                            ("▶ File", "file"),
                            ("▶ Model", "model"),
                            ("▶ Philosophy", "philosophy"),
                            ("▶ Shell", "shell"),
                            ("▶ Stop Shell", "stop_shell"),
                            ("▶ AutoHeal", "autoheal"),
                            ("▶ Help", "help"),
                            ("▶ Exit", "exit"),
                        )
                    ],
                    id="menu",
                )
            with Container(id="output_panel", classes="panel"):
                yield Static("OUTPUT", classes="panel_heading")
                yield RichLog(id="output", wrap=True, markup=False, highlight=False)
        with Horizontal(id="status_bar"):
            yield LoadingIndicator(id="activity", classes="activity")
            yield Static("", id="status_text", classes="status_text status_idle")
        yield Static("↑↓ navigate · Enter select · Tab editor", id="hint_text", classes="hint_text")

    def on_mount(self) -> None:
        self.query_one("#menu", ListView).focus()
        self.render_history(self.query_one("#output", RichLog))
        self.refresh_chrome()

    def render_history(self, log: RichLog) -> None:
        for item in self.output_history[-300:]:
            log.write(item)

    def log(self, message: str) -> None:
        for target in self.query(RichLog):
            target.write(message)
        self.output_history.extend(message.splitlines())
        self.output_history = self.output_history[-MAX_LOG_LINES:]

    def thread_log(self, message: str) -> None:
        self.call_from_thread(self.log, message)

    def trace_event_from_worker(self, event_type: str, data: dict) -> None:
        if event_type == "line":
            self.call_from_thread(self.log, f"Trace · line {data['line']}")
        elif event_type == "vars" and data:
            values = ", ".join(f"{key}={value}" for key, value in data.items())
            self.call_from_thread(self.log, "Trace · " + values)

    def model_summary(self) -> str:
        return f"Architect: {self.architect.name} · Coder: {self.coder.name}"

    def tab_strip_text(self) -> str:
        labels = []
        for index, buffer in enumerate(self.buffers):
            marker = "▸" if index == self.active_buffer_index else " "
            labels.append(f"{marker} {index + 1}:{buffer.label}")
        return "  |  ".join(labels)

    def set_status(self, mode: str, message: str) -> None:
        self.status_mode = mode
        self.status_message = message
        self.refresh_chrome()

    def refresh_chrome(self) -> None:
        text = f"{self.status_message} · {self.active_buffer.name} · {self.model_summary()} · AutoHeal {'ON' if self.auto_heal else 'OFF'}"
        classes = {
            "idle": "status_idle",
            "thinking": "status_thinking",
            "running": "status_running",
            "error": "status_error",
        }
        for widget in self.query(".status_text"):
            for name in classes.values():
                widget.remove_class(name)
            widget.add_class(classes.get(self.status_mode, "status_idle"))
            widget.update(text)
        for spinner in self.query(".activity"):
            spinner.display = self.status_mode in {"thinking", "running"}
        if isinstance(self.screen, EditorScreen):
            self.screen.refresh_status()

    def set_editor_hint(self, message: str) -> None:
        if isinstance(self.screen, EditorScreen):
            self.screen.query_one("#editor_hint", Static).update(message)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.id:
            self.handle_menu(event.item.id)

    def action_open_editor(self) -> None:
        if not isinstance(self.screen, EditorScreen):
            self.push_screen(EditorScreen())

    def action_quit_app(self) -> None:
        self.exit()

    def handle_menu(self, action: str) -> None:
        actions = {
            "editor": self.action_open_editor,
            "build": lambda: self.ask_pipeline_request("BUILD REQUEST", "build"),
            "run": self.run_active_code,
            "explain": self.explain_active_code,
            "fix": lambda: self.ask_pipeline_request("FIX DESCRIPTION", "fix"),
            "generate": lambda: self.ask_pipeline_request("GENERATE DESCRIPTION", "generate"),
            "file": self.open_file_menu,
            "model": self.open_model_menu,
            "philosophy": self.open_philosophy_menu,
            "shell": self.ask_shell,
            "stop_shell": self.stop_shell,
            "autoheal": self.toggle_auto_heal,
            "help": lambda: self.push_screen(HelpScreen()),
            "exit": self.exit,
        }
        handler = actions.get(action)
        if handler:
            handler()

    def update_active_buffer(self, text: str) -> None:
        buffer = self.active_buffer
        if buffer.text != text:
            buffer.text = text
            buffer.dirty = True
            self.refresh_chrome()

    def replace_active_code(self, text: str, language: Optional[str] = None) -> None:
        buffer = self.active_buffer
        buffer.text = text
        buffer.dirty = True
        if language:
            buffer.language = language
        self.refresh_editor_buffer()

    def refresh_editor_buffer(self) -> None:
        if isinstance(self.screen, EditorScreen):
            self.screen.refresh_from_buffer()
        self.refresh_chrome()

    def new_buffer(self) -> None:
        self.buffers.append(Buffer())
        self.active_buffer_index = len(self.buffers) - 1
        self.refresh_editor_buffer()
        self.notify("New buffer created.")

    def switch_buffer(self, direction: int) -> None:
        if len(self.buffers) > 1:
            self.active_buffer_index = (self.active_buffer_index + direction) % len(self.buffers)
            self.refresh_editor_buffer()

    def switch_to_buffer(self, index: int) -> None:
        if 0 <= index < len(self.buffers):
            self.active_buffer_index = index
            self.refresh_editor_buffer()

    def leave_editor(self) -> None:
        if not isinstance(self.screen, EditorScreen):
            return
        if self.active_buffer.dirty:
            self.push_screen(
                ConfirmScreen(
                    "LEAVE EDITOR",
                    "The active buffer has unsaved changes. Return to the menu anyway?",
                    "Leave editor",
                ),
                lambda approved: self.pop_screen() if approved else None,
            )
        else:
            self.pop_screen()

    def close_active_buffer(self) -> None:
        def close(approved: bool) -> None:
            if not approved:
                return
            self.buffers.pop(self.active_buffer_index)
            if not self.buffers:
                self.buffers = [Buffer()]
                self.active_buffer_index = 0
                if isinstance(self.screen, EditorScreen):
                    self.pop_screen()
                return
            self.active_buffer_index = min(self.active_buffer_index, len(self.buffers) - 1)
            self.refresh_editor_buffer()

        if self.active_buffer.dirty:
            self.push_screen(
                ConfirmScreen(
                    "CLOSE BUFFER",
                    f"Discard unsaved changes in {self.active_buffer.name}?",
                    "Discard",
                ),
                close,
            )
        else:
            close(True)

    def open_file_menu(self) -> None:
        self.push_screen(
            ChoiceScreen(
                "FILE",
                [
                    ("open", "Open file"),
                    ("save", "Save"),
                    ("save_as", "Save as"),
                    ("rename", "Rename"),
                    ("new", "New buffer"),
                    ("close", "Close buffer"),
                ],
            ),
            self.handle_file_choice,
        )

    def handle_file_choice(self, choice: Optional[str]) -> None:
        if choice == "open":
            self.ask_open_file()
        elif choice == "save":
            self.save_active()
        elif choice == "save_as":
            self.ask_save_as()
        elif choice == "rename":
            self.ask_rename()
        elif choice == "new":
            self.new_buffer()
        elif choice == "close":
            self.close_active_buffer()

    def ask_open_file(self) -> None:
        self.push_screen(ShortPromptScreen("OPEN FILE", "Path to source file"), self.open_file)

    def open_file(self, value: Optional[str]) -> None:
        if not value:
            return
        path = Path(value).expanduser()
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.log(f"File open error: {exc}")
            self.notify(f"Could not open file: {exc}", severity="error")
            return

        buffer = Buffer(text=source, path=path, dirty=False, language=detect_language(str(path)))
        current = self.active_buffer
        if len(self.buffers) == 1 and not current.text and not current.dirty:
            self.buffers[0] = buffer
            self.active_buffer_index = 0
        else:
            self.buffers.append(buffer)
            self.active_buffer_index = len(self.buffers) - 1
        self.refresh_editor_buffer()
        self.log(f"Opened: {path}")
        self.notify(f"Opened {path.name}")

    def save_active(self) -> None:
        if self.active_buffer.path is None:
            self.ask_save_as()
            return
        self.write_active_buffer(self.active_buffer.path)

    def ask_save_as(self) -> None:
        initial = str(self.active_buffer.path) if self.active_buffer.path else ""
        self.push_screen(ShortPromptScreen("SAVE AS", "Path and extension", initial), self.save_as)

    def save_as(self, value: Optional[str]) -> None:
        if value:
            self.write_active_buffer(Path(value).expanduser())

    def write_active_buffer(self, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.active_buffer.text, encoding="utf-8")
            self.active_buffer.path = path
            self.active_buffer.language = detect_language(str(path))
            self.active_buffer.dirty = False
            self.refresh_editor_buffer()
            self.log(f"Saved: {path}")
            self.notify(f"Saved {path.name}")
        except OSError as exc:
            self.log(f"Save error: {exc}")
            self.notify(f"Could not save file: {exc}", severity="error")

    def ask_rename(self) -> None:
        if self.active_buffer.path is None:
            self.notify("Save the buffer before renaming it.", severity="warning")
            return
        self.push_screen(ShortPromptScreen("RENAME FILE", "New path", str(self.active_buffer.path)), self.rename_active_file)

    def rename_active_file(self, value: Optional[str]) -> None:
        if not value or self.active_buffer.path is None:
            return
        target = Path(value).expanduser()
        try:
            self.active_buffer.path.rename(target)
            self.active_buffer.path = target
            self.active_buffer.language = detect_language(str(target))
            self.refresh_editor_buffer()
            self.log(f"Renamed file to: {target}")
        except OSError as exc:
            self.notify(f"Could not rename file: {exc}", severity="error")

    def editor_widget(self):
        if isinstance(self.screen, EditorScreen):
            return self.screen.query_one("#editor")
        return None

    def mutate_editor(self, text: str, cursor: tuple[int, int]) -> None:
        editor = self.editor_widget()
        if editor is None:
            return
        editor.text = text
        editor.cursor_location = cursor
        self.update_active_buffer(text)
        self.refresh_editor_buffer()

    @staticmethod
    def line_bounds(text: str, row: int) -> tuple[int, int]:
        starts = [0]
        starts.extend(index + 1 for index, char in enumerate(text) if char == "\n")
        row = max(0, min(row, len(starts) - 1))
        start = starts[row]
        end = text.find("\n", start)
        return start, len(text) if end == -1 else end + 1

    def cut_current_line(self) -> None:
        editor = self.editor_widget()
        if editor is None:
            return
        row, _ = editor.cursor_location
        start, end = self.line_bounds(editor.text, row)
        self.internal_line_clipboard = editor.text[start:end]
        updated = editor.text[:start] + editor.text[end:]
        self.mutate_editor(updated, (min(row, updated.count("\n")), 0))
        self.notify("Line cut to ANIOXAZ clipboard.")

    def paste_line(self) -> None:
        if not self.internal_line_clipboard:
            self.notify("The ANIOXAZ line clipboard is empty.", severity="warning")
            return
        editor = self.editor_widget()
        if editor is None:
            return
        row, _ = editor.cursor_location
        start, _ = self.line_bounds(editor.text, row)
        content = self.internal_line_clipboard
        if not content.endswith("\n"):
            content += "\n"
        self.mutate_editor(editor.text[:start] + content + editor.text[start:], (row, 0))

    def delete_current_line(self) -> None:
        editor = self.editor_widget()
        if editor is None:
            return
        row, _ = editor.cursor_location
        start, end = self.line_bounds(editor.text, row)
        updated = editor.text[:start] + editor.text[end:]
        self.mutate_editor(updated, (min(row, updated.count("\n")), 0))

    def ask_find(self) -> None:
        self.push_screen(ShortPromptScreen("FIND", "Search text", self.search_term), self.set_find_term)

    def set_find_term(self, value: Optional[str]) -> None:
        if value:
            self.search_term = value
            self.search_offset = -1
            self.find_next(False)

    def find_next(self, backwards: bool) -> None:
        if not self.search_term:
            self.ask_find(); return
        editor = self.editor_widget()
        if editor is None or not editor.text:
            return
        if backwards:
            start = len(editor.text) if self.search_offset <= 0 else self.search_offset - 1
            found = editor.text.rfind(self.search_term, 0, start + 1)
        else:
            start = self.search_offset + 1 if self.search_offset >= 0 else 0
            found = editor.text.find(self.search_term, start)
        if found < 0:
            self.notify("No further match.", severity="warning")
            return
        self.search_offset = found
        prefix = editor.text[:found]
        row = prefix.count("\n")
        column = len(prefix.rsplit("\n", 1)[-1])
        editor.cursor_location = (row, column)
        self.set_editor_hint(f"Found “{self.search_term}” · F3 next · Shift+F3 previous")
        if isinstance(self.screen, EditorScreen):
            self.screen.refresh_status()

    def ask_replace(self) -> None:
        self.push_screen(FindReplaceScreen(self.search_term), self.review_replace)

    def review_replace(self, response: Optional[tuple[str, str, bool]]) -> None:
        if response is None:
            return
        needle, replacement, case_sensitive = response
        source = self.active_buffer.text
        count = source.count(needle) if case_sensitive else len(re.findall(re.escape(needle), source, flags=re.IGNORECASE))
        if not count:
            self.notify("No matching text.", severity="warning")
            return
        self.push_screen(
            ConfirmScreen(
                "REPLACE ALL",
                f"Replace {count} occurrence{'s' if count != 1 else ''} of “{needle}”?",
                "Replace all",
            ),
            lambda approved: self.replace_all(response) if approved else None,
        )

    def replace_all(self, response: tuple[str, str, bool]) -> None:
        needle, replacement, case_sensitive = response
        if case_sensitive:
            updated = self.active_buffer.text.replace(needle, replacement)
        else:
            updated = re.sub(re.escape(needle), replacement, self.active_buffer.text, flags=re.IGNORECASE)
        self.replace_active_code(updated)
        self.notify("Replacement complete.")

    def ask_go_to_line(self) -> None:
        self.push_screen(ShortPromptScreen("GO TO LINE", "Line number"), self.go_to_line)

    def go_to_line(self, value: Optional[str]) -> None:
        if not value:
            return
        try:
            requested = int(value)
        except ValueError:
            self.notify("Enter a whole line number.", severity="warning")
            return
        editor = self.editor_widget()
        if editor is None:
            return
        line_count = max(1, editor.text.count("\n") + 1)
        editor.cursor_location = (max(0, min(requested, line_count) - 1), 0)
        if isinstance(self.screen, EditorScreen):
            self.screen.refresh_status()

    def toggle_word_wrap(self) -> None:
        self.word_wrap = not self.word_wrap
        self.refresh_editor_buffer()
        self.notify(f"Word wrap {'enabled' if self.word_wrap else 'disabled'}.")

    def open_model_menu(self) -> None:
        self.push_screen(
            ChoiceScreen(
                "MODEL",
                [
                    ("architect", "Load Architect model"),
                    ("coder", "Load Coder model"),
                    ("iterations", f"Iteration cap ({self.iteration_cap})"),
                ],
            ),
            self.handle_model_choice,
        )

    def handle_model_choice(self, choice: Optional[str]) -> None:
        if choice in {"architect", "coder"}:
            self.push_screen(ShortPromptScreen("LOAD " + choice.upper() + " MODEL", "Path to local GGUF model"), lambda path: self.load_model(choice, path))
        elif choice == "iterations":
            self.push_screen(ShortPromptScreen("ITERATION CAP", "Maximum repair attempts (1-20)", str(self.iteration_cap)), self.set_iteration_cap)

    def set_iteration_cap(self, value: Optional[str]) -> None:
        if not value:
            return
        try:
            cap = int(value)
            if cap < 1 or cap > 20:
                raise ValueError
        except ValueError:
            self.notify("Iteration cap must be between 1 and 20.", severity="warning")
            return
        self.iteration_cap = cap
        self.refresh_chrome()
        self.notify(f"Iteration cap set to {cap}.")

    def load_model(self, role: str, path: Optional[str]) -> None:
        if not path:
            return
        self.set_status("thinking", f"Loading {role} model…")
        self.load_model_worker(role, path)

    @work(thread=True)
    def load_model_worker(self, role: str, path: str) -> None:
        model = self.architect if role == "architect" else self.coder
        success, message = model.load(path)
        self.call_from_thread(self.finish_model_load, success, message)

    def finish_model_load(self, success: bool, message: str) -> None:
        self.set_status("idle" if success else "error", "Ready" if success else "Model error")
        self.log(message)
        self.notify(message, severity="information" if success else "error")

    def open_philosophy_menu(self) -> None:
        self.push_screen(
            ChoiceScreen(
                "PHILOSOPHY FILE",
                [
                    ("create", "Create new Philosophy File"),
                    ("load", "Load existing Philosophy File"),
                    ("view", "View current Philosophy File"),
                    ("edit", "Edit current Philosophy File"),
                    ("replace", "Replace from file"),
                    ("clear", "Clear current Philosophy File"),
                ],
            ),
            self.handle_philosophy_choice,
        )

    def handle_philosophy_choice(self, choice: Optional[str]) -> None:
        if choice == "create":
            self.push_screen(ShortPromptScreen("CREATE PHILOSOPHY FILE", "Path for markdown file (.md)"), self.create_philosophy)
        elif choice in {"load", "replace"}:
            self.push_screen(ShortPromptScreen("LOAD PHILOSOPHY FILE", "Path to markdown file"), self.load_philosophy)
        elif choice == "view":
            self.view_philosophy()
        elif choice == "edit":
            self.edit_philosophy()
        elif choice == "clear":
            self.push_screen(
                ConfirmScreen(
                    "CLEAR PHILOSOPHY",
                    "Clear this session's Philosophy File? The file on disk is retained.",
                    "Clear",
                ),
                lambda approved: self.clear_philosophy() if approved else None,
            )

    def create_philosophy(self, value: Optional[str]) -> None:
        if value:
            self.philosophy_path = Path(value).expanduser()
            self.philosophy_text = "# ANIOXAZ Philosophy\n\n"
            self.open_philosophy_editor()

    def load_philosophy(self, value: Optional[str]) -> None:
        if not value:
            return
        path = Path(value).expanduser()
        try:
            self.philosophy_text = path.read_text(encoding="utf-8")
            self.philosophy_path = path
            self.log(f"Philosophy File loaded: {path}")
            self.notify(f"Loaded {path.name}")
        except OSError as exc:
            self.notify(f"Could not load Philosophy File: {exc}", severity="error")

    def view_philosophy(self) -> None:
        if not self.philosophy_text:
            self.notify("No Philosophy File is loaded.", severity="warning")
            return
        self.push_screen(PhilosophyViewScreen(self.philosophy_text, self.philosophy_path))

    def edit_philosophy(self) -> None:
        if not self.philosophy_text:
            self.notify("Create or load a Philosophy File first.", severity="warning")
            return
        self.open_philosophy_editor()

    def open_philosophy_editor(self) -> None:
        self.push_screen(
            PromptScreen(
                "EDIT PHILOSOPHY FILE",
                "Persistent guidance sent to Architect only.",
                self.philosophy_text,
                "Save philosophy",
            ),
            self.save_philosophy_text,
        )

    def save_philosophy_text(self, value: Optional[str]) -> None:
        if value is None:
            return
        self.philosophy_text = value
        if self.philosophy_path is None:
            self.notify("Choose a Philosophy File path first.", severity="warning")
            return
        try:
            self.philosophy_path.parent.mkdir(parents=True, exist_ok=True)
            self.philosophy_path.write_text(value, encoding="utf-8")
            self.log(f"Philosophy File saved: {self.philosophy_path}")
            self.notify("Philosophy File saved.")
        except OSError as exc:
            self.notify(f"Could not save Philosophy File: {exc}", severity="error")

    def clear_philosophy(self) -> None:
        self.philosophy_text = ""
        self.philosophy_path = None
        self.log("Philosophy File cleared for this session.")
        self.notify("Philosophy File cleared.")

    def ask_shell(self) -> None:
        self.push_screen(PromptScreen("SHELL", "Run a local shell command. Output streams to the log.", submit_label="Run command"), self.run_shell)

    def run_shell(self, command: Optional[str]) -> None:
        if command:
            self.terminal.run_command(command)
            self.set_status("running", "Shell running…")

    def stop_shell(self) -> None:
        if self.terminal.stop():
            self.log("Shell stop requested.")
            self.notify("Shell stop requested.")
        else:
            self.notify("No shell command is running.", severity="warning")

    def toggle_auto_heal(self) -> None:
        self.auto_heal = not self.auto_heal
        self.refresh_chrome()
        self.notify(f"AutoHeal {'enabled' if self.auto_heal else 'disabled'}.")

    def ask_pipeline_request(self, title: str, mode: str) -> None:
        self.push_screen(PromptScreen(title, "Describe the task or fix request.", submit_label="Run"), lambda value: self.run_pipeline(mode, value))

    def run_pipeline(self, mode: str, request: Optional[str]) -> None:
        if not request or not request.strip():
            self.notify("Write a request first.", severity="warning")
            return
        if not (self.architect.loaded or self.coder.loaded):
            self.notify("At least one model must be loaded.", severity="error")
            return

        self.pipeline_active = True
        source = self.active_buffer.text
        message = {"build": "Building and running request…", "fix": "Applying a repair cycle…", "generate": "Generating code from request…"}.get(mode, "Processing request…")
        self.set_status("thinking", message)

        plan = ""
        if self.architect.loaded:
            try:
                plan = self.architect.plan(request.strip(), self.philosophy_text, source)
                self.log(f"Architect plan:\n{plan}")
            except RuntimeError as exc:
                self.notify(str(exc), severity="error")
                self.set_status("error", "Planning failed")
                return

        if self.coder.loaded:
            try:
                generated = self.coder.from_plan(plan, source) if plan else self.coder.fallback(request.strip(), source)
            except RuntimeError as exc:
                self.notify(str(exc), severity="error")
                self.set_status("error", "Generation failed")
                return
        else:
            generated = source

        if self.coder.loaded:
            self.replace_active_code(generated, detect_language(self.active_buffer.path.name if self.active_buffer.path else None, request))
        self.set_status("running", "Executing generated code…")
        result = self.executor.run(self.active_buffer.text, self.active_buffer.language)

        if result.error is None:
            if self.architect.loaded:
                summary = self.architect.summarize(request.strip(), result.stdout, self.philosophy_text)
                self.log(summary)
                self.notify("Request completed successfully.", severity="information")
            else:
                self.log(result.stdout or "Completed successfully.")
                self.notify("Request completed successfully.", severity="information")
            self.set_status("idle", "Ready")
            self.pipeline_active = False
            return

        if self.auto_heal and self.architect.loaded and self.coder.loaded:
            self.set_status("thinking", "Diagnosing failure and repairing…")
            try:
                classification, explanation, instruction = self.architect.diagnose(plan or "No plan available.", result.error, "")
                self.log(f"Classification: {classification}\n{explanation}\nRepair instruction: {instruction}")
                repaired = self.coder.repair(instruction, self.active_buffer.text)
                self.replace_active_code(repaired, self.active_buffer.language)
                self.log("Repair attempt applied.")
                rerun = self.executor.run(self.active_buffer.text, self.active_buffer.language)
                if rerun.error is None:
                    if self.architect.loaded:
                        self.log(self.architect.summarize(request.strip(), rerun.stdout, self.philosophy_text))
                    else:
                        self.log(rerun.stdout or "Completed after repair.")
                    self.set_status("idle", "Ready")
                    self.pipeline_active = False
                    return
                self.notify("Auto-heal did not fully resolve the issue.", severity="warning")
                self.log(rerun.error)
            except RuntimeError as exc:
                self.notify(str(exc), severity="error")
        self.set_status("error", "Execution failed")
        self.log(result.error)
        self.notify(result.error, severity="error")
        self.pipeline_active = False

    def run_active_code(self) -> None:
        if not self.active_buffer.text.strip():
            self.notify("There is no code in the active buffer.", severity="warning")
            return
        self.set_status("running", "Running active code…")
        result = self.executor.run(self.active_buffer.text, self.active_buffer.language)
        if result.error is None:
            output = result.stdout or "(no output)"
            self.log(f"Program output:\n{output}")
            self.notify("Code executed successfully.", severity="information")
            self.set_status("idle", "Ready")
        else:
            self.log(result.error)
            self.notify(result.error, severity="error")
            self.set_status("error", "Execution failed")

    def explain_active_code(self) -> None:
        if not self.active_buffer.text.strip():
            self.notify("The active buffer is empty.", severity="warning")
            return
        if not self.architect.loaded:
            self.notify("Load the Architect model to explain code.", severity="warning")
            return
        self.set_status("thinking", "Explaining the current code…")
        try:
            explanation = self.architect.explain(self.active_buffer.text, self.philosophy_text)
        except RuntimeError as exc:
            self.notify(str(exc), severity="error")
            self.set_status("error", "Explanation failed")
            return
        self.log(f"Architect explanation:\n{explanation}")
        self.notify("Code explanation generated.", severity="information")
        self.set_status("idle", "Ready")
