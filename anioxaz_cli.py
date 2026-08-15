#!/usr/bin/env python3
"""
anioxaz_cli.py - VERTICAL MENU version with hidden editor
Author: Rehan Aman
"""

import curses
import curses.ascii
import threading
import subprocess
import sys
import os
import tempfile
import time
import queue
import json
from typing import List, Optional, Tuple, Dict, Any

# Try to import llama-cpp-python
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

# ===========================
# CONFIGURATION
# ===========================
EXECUTION_TIMEOUT = 10
EDITOR_TAB_WIDTH = 4

# ===========================
# MODULE 1: LOCAL AI ASSISTANT
# ===========================
class AIAssistant:
    def __init__(self):
        self.llm = None
        self.model_path = None

    def load_model(self, path: str) -> bool:
        if Llama is None:
            return False
        try:
            self.llm = Llama(model_path=path, n_ctx=2048, n_threads=4, verbose=False)
            self.model_path = path
            return True
        except Exception:
            return False

    def _ask(self, prompt: str) -> str:
        if self.llm is None:
            return "[Error: No model loaded. Use Model menu to load.]"
        try:
            output = self.llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.2,
                stop=["\n\n", "```"],
            )
            return output["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[Model Error: {str(e)}]"

    def generate_code(self, description: str) -> str:
        prompt = f"Write Python code that does:\n{description}\n\nOnly output the code, no explanations."
        return self._ask(prompt)

    def fix_code(self, code: str, error: str) -> str:
        prompt = f"The following Python code:\n```python\n{code}\n```\nproduces this error:\n{error}\n\nProvide corrected code. Only code."
        return self._ask(prompt)

    def explain_code(self, code: str) -> str:
        prompt = f"Explain this Python code:\n```python\n{code}\n```"
        return self._ask(prompt)

# ===========================
# MODULE 2: TRACER
# ===========================
class Tracer:
    def __init__(self, callback):
        self.callback = callback

    def run_with_tracing(self, code: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            user_file = f.name

        wrapper = f"""
import sys, json, trace

def trace_callback(frame, event, arg):
    if event == 'line':
        sys.stderr.write(f'TRACE_LINE:{{frame.f_lineno}}\\n')
        sys.stderr.flush()
        locals_dict = {{k: repr(v) for k, v in frame.f_locals.items() if not k.startswith('__')}}
        sys.stderr.write(f'TRACE_VARS:{{json.dumps(locals_dict)}}\\n')
        sys.stderr.flush()
    return trace_callback

sys.settrace(trace_callback)
exec(open(r'{user_file}').read())
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as wf:
            wf.write(wrapper)
            wrapper_file = wf.name

        output = []
        error = None
        try:
            proc = subprocess.Popen(
                [sys.executable, wrapper_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=os.environ.copy()
            )
            stdout_q = queue.Queue()
            stderr_q = queue.Queue()

            def read_pipe(pipe, q):
                for line in iter(pipe.readline, ''):
                    q.put(line)
                pipe.close()

            t1 = threading.Thread(target=read_pipe, args=(proc.stdout, stdout_q))
            t2 = threading.Thread(target=read_pipe, args=(proc.stderr, stderr_q))
            t1.start()
            t2.start()

            while proc.poll() is None:
                self._process_queues(stdout_q, stderr_q, output)
                time.sleep(0.05)

            self._process_queues(stdout_q, stderr_q, output)

            if proc.returncode != 0:
                error = f"Process exited with code {proc.returncode}"
        except subprocess.TimeoutExpired:
            proc.kill()
            error = "Execution timed out"
        except Exception as e:
            error = str(e)
        finally:
            try:
                os.unlink(user_file)
            except:
                pass
            try:
                os.unlink(wrapper_file)
            except:
                pass

        return output, error

    def _process_queues(self, stdout_q, stderr_q, output):
        while not stderr_q.empty():
            line = stderr_q.get_nowait()
            if line.startswith('TRACE_LINE:'):
                line_no = int(line.split(':')[1].strip())
                self.callback('line', {'line': line_no})
            elif line.startswith('TRACE_VARS:'):
                try:
                    vars_data = json.loads(line[len('TRACE_VARS:'):].strip())
                    self.callback('vars', vars_data)
                except:
                    pass
            else:
                output.append(('stderr', line))
        while not stdout_q.empty():
            line = stdout_q.get_nowait()
            output.append(('stdout', line))

# ===========================
# MODULE 3: TERMINAL
# ===========================
class Terminal:
    def __init__(self, output_callback):
        self.output_callback = output_callback
        self.process = None

    def run_command(self, command: str):
        if not command.strip():
            return
        def target():
            self.output_callback(f"\n$ {command}\n")
            try:
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                self.process = proc
                for line in iter(proc.stdout.readline, ''):
                    self.output_callback(line)
                proc.stdout.close()
                proc.wait()
                self.output_callback(f"\n[Finished with code {proc.returncode}]\n")
            except Exception as e:
                self.output_callback(f"Error: {str(e)}\n")
            self.process = None
        threading.Thread(target=target, daemon=True).start()

    def stop(self):
        if self.process:
            self.process.terminate()

# ===========================
# MODULE 4: CURSES APPLICATION (vertical menu, editor hidden by default)
# ===========================
class ReplitApp:
    def __init__(self):
        self.ai = AIAssistant()
        self.terminal = Terminal(self.output_callback)
        self.tracer = Tracer(self.trace_callback)

        # UI state
        self.code_lines = [""]
        self.cursor_y = 0
        self.cursor_x = 0
        self.scroll_y = 0
        self.scroll_x = 0
        self.filename = None
        self.running = False
        self.auto_heal = False

        # Output/trace
        self.output_lines = ["Welcome to anioxaz_cli! Use ↑/↓ to navigate, Enter to select, ESC to return."]
        self.trace_events = []
        self.output_scroll = 0

        # UI queue
        self.ui_queue = queue.Queue()

        # State: "menu" | "submenu" | "editor" | "shell" | "prompt"
        self.state = "menu"
        self.menu_selection = 0
        self.main_menu = [
            ("Editor", "editor"),
            ("Run", "run"),
            ("Explain", "explain"),
            ("Fix", "fix"),
            ("Generate", "generate"),
            ("File", "file_submenu"),
            ("Model", "model"),
            ("Shell", "shell"),
            ("AutoHeal", "autoheal"),
            ("Help", "help"),
            ("Exit", "exit")
        ]
        self.file_submenu = [
            ("Open", "open"),
            ("Save", "save"),
            ("Save As", "save_as"),
            ("Rename", "rename"),
            ("Back", "back")
        ]
        self.submenu_selection = 0

        # Prompt
        self.prompt_text = ""
        self.prompt_buffer = ""
        self.prompt_callback = None

        # Shell mode
        self.shell_buffer = ""

        # Terminal dimensions
        self.rows = 0
        self.cols = 0
        self.banner_rows = 4
        self.menu_x = 2
        self.menu_y = self.banner_rows + 1
        self.editor_rows = 0
        self.output_rows = 0
        self.status_rows = 1

        self.stdscr = None

        # Colors
        self.COLOR_RED = 1
        self.COLOR_GREEN = 2
        self.COLOR_BLUE = 3
        self.COLOR_YELLOW = 4
        self.COLOR_MAGENTA = 5
        self.COLOR_CYAN = 6
        self.COLOR_WHITE = 7
        self.COLOR_HIGHLIGHT = 8
        self.COLOR_STATUS = 9
        self.COLOR_PROMPT = 10
        self.COLOR_SHELL = 11

    # ---------- Callbacks ----------
    def output_callback(self, text):
        self.ui_queue.put(('output', text))

    def trace_callback(self, event_type, data):
        self.ui_queue.put(('trace', (event_type, data)))

    # ---------- Drawing ----------
    def _init_colors(self):
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(self.COLOR_RED, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_GREEN, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_BLUE, curses.COLOR_BLUE, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_YELLOW, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_MAGENTA, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_CYAN, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_WHITE, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(self.COLOR_STATUS, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(self.COLOR_PROMPT, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(self.COLOR_SHELL, curses.COLOR_GREEN, curses.COLOR_BLACK)

    def _draw_banner(self, stdscr):
        banner = [
            " █████  ███    ██ ██  ██████  ██   ██  █████  ███████ ██  ",
            "██   ██ ████   ██ ██ ██    ██  ██ ██  ██   ██    ███  ██  ",
            "███████ ██ ██  ██ ██ ██    ██   ███   ███████   ███   ██  ",
            "██   ██ ██  ██ ██ ██ ██    ██  ██ ██  ██   ██  ███    ██  ",
            "██   ██ ██   ████ ██  ██████  ██   ██ ██   ██ ███████ ██  ",
        ]
        for i, line in enumerate(banner[:self.banner_rows]):
            if i >= self.rows:
                break
            try:
                stdscr.addstr(i, 0, line[:self.cols], curses.color_pair(self.COLOR_RED) | curses.A_BOLD)
            except:
                pass

    def _draw_vertical_menu(self, stdscr, items, selection, title=""):
        y = self.menu_y
        x = self.menu_x
        if title:
            try:
                stdscr.addstr(y, x, title, curses.color_pair(self.COLOR_CYAN) | curses.A_BOLD)
            except:
                pass
            y += 1
        for idx, (label, _) in enumerate(items):
            color = curses.color_pair(self.COLOR_WHITE)
            if idx == selection:
                color = curses.color_pair(self.COLOR_HIGHLIGHT) | curses.A_BOLD
            elif idx % 2 == 0:
                color = curses.color_pair(self.COLOR_GREEN)
            else:
                color = curses.color_pair(self.COLOR_YELLOW)
            try:
                stdscr.addstr(y + idx, x, f"  {label}  ", color)
            except:
                pass

    def _draw_editor(self, stdscr):
        # Only draw if state is editor
        if self.state != "editor":
            return
        start_y = self.banner_rows + 2
        h = self.editor_rows
        w = self.cols
        if h <= 0 or w <= 0:
            return
        # Draw a border around the editor
        try:
            stdscr.attron(curses.color_pair(self.COLOR_BLUE) | curses.A_DIM)
            stdscr.hline(start_y - 1, 0, curses.ACS_HLINE, w)
            stdscr.attroff(curses.color_pair(self.COLOR_BLUE) | curses.A_DIM)
        except:
            pass
        line_num_width = len(str(len(self.code_lines))) + 1
        if line_num_width >= w:
            line_num_width = 1
        for i in range(h):
            line_idx = i + self.scroll_y
            if line_idx >= len(self.code_lines):
                break
            line = self.code_lines[line_idx]
            num_str = f"{line_idx+1:>{line_num_width-1}} " if line_idx >= 0 else " "
            try:
                stdscr.addstr(start_y + i, 0, num_str[:w], curses.color_pair(self.COLOR_MAGENTA) | curses.A_DIM)
            except:
                pass
            if len(line) > self.scroll_x:
                disp = line[self.scroll_x:]
            else:
                disp = ""
            max_disp = w - line_num_width
            if max_disp <= 0:
                continue
            if len(disp) > max_disp:
                disp = disp[:max_disp-1] + "…"
            try:
                stdscr.addstr(start_y + i, line_num_width, disp[:max_disp])
            except:
                pass
        # Cursor
        cursor_y = start_y + self.cursor_y - self.scroll_y
        cursor_x = self.cursor_x - self.scroll_x + line_num_width
        if 0 <= cursor_y < start_y + h and 0 <= cursor_x < w:
            stdscr.move(cursor_y, cursor_x)

    def _draw_output(self, stdscr):
        start_y = self.banner_rows + self.editor_rows + 3
        if self.state == "menu" or self.state == "submenu":
            # menu mode: output starts right after menu
            # menu ends at menu_y + len(menu_items) - but we calculate a fixed offset
            # Use the same start_y as if editor hidden
            start_y = self.banner_rows + 3
        h = self.output_rows
        w = self.cols
        if h <= 0 or w <= 0:
            return
        # Draw a separator line
        try:
            stdscr.addstr(start_y - 1, 0, "─" * min(w, 80), curses.color_pair(self.COLOR_BLUE) | curses.A_DIM)
        except:
            pass
        start = max(0, len(self.output_lines) - h)
        for i, line in enumerate(self.output_lines[start:]):
            if i >= h:
                break
            try:
                stdscr.addstr(start_y + i, 0, line[:w-1])
            except:
                pass

    def _draw_status(self, stdscr):
        y = self.rows - self.status_rows
        w = self.cols
        if y < 0:
            return
        model_status = self.ai.model_path if self.ai.model_path else "No model"
        filename = self.filename or "Untitled"
        mode = "RUNNING" if self.running else "EDIT"
        state_str = self.state.upper()
        status = f"[{mode}] {filename} | Model: {model_status} | Auto‑heal: {'ON' if self.auto_heal else 'OFF'} | State: {state_str}"
        if len(status) > w-1:
            status = status[:w-1]
        try:
            stdscr.addstr(y, 0, status, curses.color_pair(self.COLOR_STATUS) | curses.A_BOLD)
        except:
            pass

    def _draw_prompt(self, stdscr):
        if self.state != "prompt":
            return
        y = self.rows - self.status_rows - 1
        w = self.cols
        if y < 0:
            return
        stdscr.move(y, 0)
        stdscr.clrtoeol()
        text = self.prompt_text + self.prompt_buffer
        try:
            stdscr.addstr(y, 0, text[:w-1], curses.color_pair(self.COLOR_PROMPT) | curses.A_BOLD)
        except:
            pass
        pos = len(self.prompt_text) + len(self.prompt_buffer)
        if pos < w:
            stdscr.move(y, pos)

    def _draw_shell(self, stdscr):
        if self.state != "shell":
            return
        y = self.rows - self.status_rows - 1
        w = self.cols
        if y < 0:
            return
        stdscr.move(y, 0)
        stdscr.clrtoeol()
        text = "$ " + self.shell_buffer
        try:
            stdscr.addstr(y, 0, text[:w-1], curses.color_pair(self.COLOR_SHELL) | curses.A_BOLD)
        except:
            pass
        pos = len(text)
        if pos < w:
            stdscr.move(y, pos)

    def _redraw(self):
        stdscr = self.stdscr
        stdscr.clear()
        self._draw_banner(stdscr)
        if self.state == "menu":
            self._draw_vertical_menu(stdscr, self.main_menu, self.menu_selection)
        elif self.state == "submenu":
            self._draw_vertical_menu(stdscr, self.file_submenu, self.submenu_selection, "FILE MENU")
        elif self.state == "editor":
            self._draw_editor(stdscr)
        elif self.state == "shell":
            self._draw_shell(stdscr)
        elif self.state == "prompt":
            self._draw_prompt(stdscr)
        # Always draw output and status
        self._draw_output(stdscr)
        self._draw_status(stdscr)
        stdscr.refresh()

    # ---------- Input Handling ----------
    def _handle_key(self, key):
        if self.state == "menu":
            self._handle_menu_key(key)
        elif self.state == "submenu":
            self._handle_submenu_key(key)
        elif self.state == "editor":
            self._handle_editor_key(key)
        elif self.state == "shell":
            self._handle_shell_key(key)
        elif self.state == "prompt":
            self._handle_prompt_key(key)

    # ---------- Menu Navigation ----------
    def _handle_menu_key(self, key):
        if key == curses.KEY_UP:
            self.menu_selection = (self.menu_selection - 1) % len(self.main_menu)
        elif key == curses.KEY_DOWN:
            self.menu_selection = (self.menu_selection + 1) % len(self.main_menu)
        elif key == 10 or key == 13:  # Enter
            self._execute_menu_action(self.main_menu[self.menu_selection][1])
        elif key == 27:  # ESC – no effect in main menu
            pass

    def _handle_submenu_key(self, key):
        if key == curses.KEY_UP:
            self.submenu_selection = (self.submenu_selection - 1) % len(self.file_submenu)
        elif key == curses.KEY_DOWN:
            self.submenu_selection = (self.submenu_selection + 1) % len(self.file_submenu)
        elif key == 10 or key == 13:
            action = self.file_submenu[self.submenu_selection][1]
            self._execute_submenu_action(action)
        elif key == 27:  # ESC – back to main menu
            self.state = "menu"

    # ---------- Editor ----------
    def _handle_editor_key(self, key):
        if key == 27:  # ESC – return to menu
            self.state = "menu"
            return
        # Standard editor keys
        if key == curses.KEY_ENTER or key == 10 or key == 13:
            line = self.code_lines[self.cursor_y]
            self.code_lines.insert(self.cursor_y + 1, line[self.cursor_x:])
            self.code_lines[self.cursor_y] = line[:self.cursor_x]
            self.cursor_y += 1
            self.cursor_x = 0
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.cursor_x > 0:
                line = self.code_lines[self.cursor_y]
                self.code_lines[self.cursor_y] = line[:self.cursor_x-1] + line[self.cursor_x:]
                self.cursor_x -= 1
            elif self.cursor_y > 0:
                prev_line = self.code_lines[self.cursor_y-1]
                curr_line = self.code_lines[self.cursor_y]
                self.code_lines[self.cursor_y-1] = prev_line + curr_line
                del self.code_lines[self.cursor_y]
                self.cursor_y -= 1
                self.cursor_x = len(prev_line)
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_DC:
            line = self.code_lines[self.cursor_y]
            if self.cursor_x < len(line):
                self.code_lines[self.cursor_y] = line[:self.cursor_x] + line[self.cursor_x+1:]
            elif self.cursor_y < len(self.code_lines)-1:
                self.code_lines[self.cursor_y] = line + self.code_lines[self.cursor_y+1]
                del self.code_lines[self.cursor_y+1]
            return
        if key == curses.KEY_LEFT:
            if self.cursor_x > 0:
                self.cursor_x -= 1
            elif self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = len(self.code_lines[self.cursor_y])
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_RIGHT:
            if self.cursor_x < len(self.code_lines[self.cursor_y]):
                self.cursor_x += 1
            elif self.cursor_y < len(self.code_lines)-1:
                self.cursor_y += 1
                self.cursor_x = 0
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_UP:
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = min(self.cursor_x, len(self.code_lines[self.cursor_y]))
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_DOWN:
            if self.cursor_y < len(self.code_lines)-1:
                self.cursor_y += 1
                self.cursor_x = min(self.cursor_x, len(self.code_lines[self.cursor_y]))
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_HOME:
            self.cursor_x = 0
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_END:
            self.cursor_x = len(self.code_lines[self.cursor_y])
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_PPAGE:
            self.cursor_y = max(0, self.cursor_y - self.editor_rows)
            self._ensure_cursor_visible()
            return
        if key == curses.KEY_NPAGE:
            self.cursor_y = min(len(self.code_lines)-1, self.cursor_y + self.editor_rows)
            self._ensure_cursor_visible()
            return
        if key == ord('\t'):
            line = self.code_lines[self.cursor_y]
            self.code_lines[self.cursor_y] = line[:self.cursor_x] + " " * EDITOR_TAB_WIDTH + line[self.cursor_x:]
            self.cursor_x += EDITOR_TAB_WIDTH
            self._ensure_cursor_visible()
            return
        if 32 <= key <= 126:
            line = self.code_lines[self.cursor_y]
            self.code_lines[self.cursor_y] = line[:self.cursor_x] + chr(key) + line[self.cursor_x:]
            self.cursor_x += 1
            self._ensure_cursor_visible()
            return

    def _ensure_cursor_visible(self):
        h = self.editor_rows
        w = self.cols
        line_num_width = len(str(len(self.code_lines))) + 1
        if self.cursor_y < self.scroll_y:
            self.scroll_y = self.cursor_y
        elif self.cursor_y >= self.scroll_y + h:
            self.scroll_y = self.cursor_y - h + 1
        if self.cursor_x < self.scroll_x:
            self.scroll_x = self.cursor_x
        elif self.cursor_x >= self.scroll_x + (w - line_num_width):
            self.scroll_x = self.cursor_x - (w - line_num_width) + 1
        self.scroll_x = max(0, self.scroll_x)

    # ---------- Shell ----------
    def _handle_shell_key(self, key):
        if key == 27:  # ESC – back to menu
            self.state = "menu"
            return
        if key == 10 or key == 13:  # Enter – execute command
            if self.shell_buffer.strip():
                self.terminal.run_command(self.shell_buffer)
            self.shell_buffer = ""
            return
        if key == curses.KEY_BACKSPACE or key == 127:
            self.shell_buffer = self.shell_buffer[:-1]
            return
        if 32 <= key <= 126:
            self.shell_buffer += chr(key)
            return

    # ---------- Prompt ----------
    def _handle_prompt_key(self, key):
        if key == 10 or key == 13:
            callback = self.prompt_callback
            buf = self.prompt_buffer
            self.state = "menu"  # return to menu after prompt
            self.prompt_buffer = ""
            self.prompt_text = ""
            self.prompt_callback = None
            if callback:
                callback(buf)
            return
        if key == 27:  # ESC – cancel
            self.state = "menu"
            self.prompt_buffer = ""
            self.prompt_text = ""
            self.prompt_callback = None
            return
        if key == curses.KEY_BACKSPACE or key == 127:
            self.prompt_buffer = self.prompt_buffer[:-1]
            return
        if 32 <= key <= 126:
            self.prompt_buffer += chr(key)
            return

    # ---------- Actions ----------
    def _execute_menu_action(self, action):
        if action == "editor":
            self.state = "editor"
        elif action == "run":
            self._run_code()
        elif action == "explain":
            self._ai_explain()
        elif action == "fix":
            self._start_prompt("Error description: ", self._ai_fix_with_desc)
        elif action == "generate":
            self._start_prompt("Description: ", self._ai_generate_with_desc)
        elif action == "file_submenu":
            self.state = "submenu"
            self.submenu_selection = 0
        elif action == "model":
            self._start_prompt("Path to GGUF model: ", self._load_model)
        elif action == "shell":
            self.state = "shell"
            self.shell_buffer = ""
        elif action == "autoheal":
            self.auto_heal = not self.auto_heal
            self.output_callback(f"Auto‑heal {'enabled' if self.auto_heal else 'disabled'}\n")
        elif action == "help":
            self._show_help()
        elif action == "exit":
            sys.exit(0)

    def _execute_submenu_action(self, action):
        if action == "open":
            self._start_prompt("Filename to open: ", self._open_file)
        elif action == "save":
            self._save_file()
        elif action == "save_as":
            self._start_prompt("Save as: ", self._save_file_as)
        elif action == "rename":
            self._start_prompt("New filename: ", self._rename_file)
        elif action == "back":
            self.state = "menu"

    def _start_prompt(self, prompt, callback):
        self.state = "prompt"
        self.prompt_text = prompt
        self.prompt_buffer = ""
        self.prompt_callback = callback

    # ---------- File Operations ----------
    def _save_file(self):
        if not self.filename:
            self.output_callback("No filename set. Use Save As.\n")
            return
        try:
            with open(self.filename, 'w') as f:
                f.write('\n'.join(self.code_lines))
            self.output_callback(f"Saved: {self.filename}\n")
        except Exception as e:
            self.output_callback(f"Save error: {e}\n")

    def _save_file_as(self, path):
        if not path:
            return
        try:
            with open(path, 'w') as f:
                f.write('\n'.join(self.code_lines))
            self.filename = path
            self.output_callback(f"Saved as: {path}\n")
        except Exception as e:
            self.output_callback(f"Save error: {e}\n")

    def _rename_file(self, newname):
        if not newname:
            return
        old = self.filename
        if old and os.path.exists(old):
            try:
                os.rename(old, newname)
                self.filename = newname
                self.output_callback(f"Renamed {old} → {newname}\n")
            except Exception as e:
                self.output_callback(f"Rename error: {e}\n")
        else:
            self.output_callback("No existing file to rename.\n")

    def _open_file(self, path):
        try:
            with open(path, 'r') as f:
                content = f.read()
            self.code_lines = content.splitlines()
            if not self.code_lines:
                self.code_lines = [""]
            self.filename = path
            self.cursor_y = 0
            self.cursor_x = 0
            self.scroll_y = 0
            self.scroll_x = 0
            self.output_callback(f"Opened: {path}\n")
        except Exception as e:
            self.output_callback(f"Open error: {e}\n")

    def _load_model(self, path):
        if self.ai.load_model(path):
            self.output_callback(f"Model loaded: {path}\n")
        else:
            self.output_callback(f"Failed to load model from {path}\n")

    # ---------- AI & Run ----------
    def _run_code(self):
        if self.running:
            return
        code = '\n'.join(self.code_lines)
        if not code.strip():
            self.output_callback("No code to run.\n")
            return

        self.running = True
        self.output_callback("=== Execution started ===\n")
        self.ui_queue.put(('clear_output', None))

        def execute():
            output, error = self.tracer.run_with_tracing(code)
            for stream, line in output:
                self.output_callback(line)
            if error:
                self.output_callback(f"\n[ERROR] {error}\n")
                if self.auto_heal:
                    self._auto_heal(code, error)
            else:
                self.output_callback("\n=== Execution finished ===\n")
            self.running = False

        threading.Thread(target=execute, daemon=True).start()

    def _ai_explain(self):
        code = '\n'.join(self.code_lines)
        if not code.strip():
            self.output_callback("No code to explain.\n")
            return
        self.output_callback("--- Explanation ---\n")
        resp = self.ai.explain_code(code)
        self.output_callback(resp + "\n")

    def _ai_fix_with_desc(self, desc):
        if not desc:
            self.output_callback("No error description.\n")
            return
        code = '\n'.join(self.code_lines)
        self.output_callback("--- AI Fixing ---\n")
        resp = self.ai.fix_code(code, desc)
        if resp:
            self.code_lines = resp.splitlines()
            if not self.code_lines:
                self.code_lines = [""]
            self.cursor_y = 0
            self.cursor_x = 0
            self.scroll_y = 0
            self.scroll_x = 0
            self.output_callback("Code updated.\n")
        else:
            self.output_callback("No fix generated.\n")

    def _ai_generate_with_desc(self, desc):
        if not desc:
            self.output_callback("No description.\n")
            return
        self.output_callback("--- Generating ---\n")
        resp = self.ai.generate_code(desc)
        if resp:
            self.code_lines = resp.splitlines()
            if not self.code_lines:
                self.code_lines = [""]
            self.cursor_y = 0
            self.cursor_x = 0
            self.scroll_y = 0
            self.scroll_x = 0
            self.output_callback("Code generated.\n")
        else:
            self.output_callback("Generation failed.\n")

    def _auto_heal(self, code, error):
        self.output_callback("\n[Auto‑heal] Attempting to fix...\n")
        resp = self.ai.fix_code(code, error)
        if resp and resp != code:
            self.code_lines = resp.splitlines()
            if not self.code_lines:
                self.code_lines = [""]
            self.output_callback("[Auto‑heal] Code fixed. Re‑running...\n")
            self._run_code()
        else:
            self.output_callback("[Auto‑heal] No fix found.\n")

    def _show_help(self):
        help_text = """
ANIOXAZ – Local AI Coding Partner (menu-driven)

Main Menu:
  Editor  – enter the code editor (ESC to return)
  Run     – execute code with live tracing
  Explain – AI explains your code
  Fix     – AI fixes your code (asks for error description)
  Generate – AI generates code from a description
  File    – submenu: Open, Save, Save As, Rename
  Model   – load a GGUF model (path)
  Shell   – run shell commands (ESC to return)
  AutoHeal – toggle automatic healing on errors
  Help    – show this help
  Exit    – quit

Use ↑/↓ to navigate, Enter to select, ESC to go back to main menu.
In Editor: type code, use arrow keys, Home/End, Page Up/Down, Tab for indent.
"""
        self.output_callback(help_text)

    # ---------- Main Loop ----------
    def run(self, stdscr):
        self.stdscr = stdscr
        self.rows, self.cols = stdscr.getmaxyx()

        if self.rows < 20 or self.cols < 50:
            stdscr.clear()
            stdscr.addstr(0, 0, "Terminal too small! Please resize to at least 20x50.")
            stdscr.addstr(1, 0, "Press any key to exit.")
            stdscr.refresh()
            stdscr.getch()
            return

        curses.curs_set(1)
        stdscr.nodelay(0)
        curses.noecho()
        self._init_colors()

        # Calculate regions
        self.editor_rows = max(5, self.rows - self.banner_rows - 8)
        self.output_rows = max(3, self.rows - self.banner_rows - self.editor_rows - 6)

        self._redraw()

        while True:
            try:
                key = stdscr.getch()
            except KeyboardInterrupt:
                break

            if key == -1:
                continue

            self._process_ui_queue()
            self._handle_key(key)
            self._redraw()

        curses.endwin()

    def _process_ui_queue(self):
        while not self.ui_queue.empty():
            item = self.ui_queue.get_nowait()
            if item[0] == 'output':
                text = item[1]
                self.output_lines.append(text)
                if len(self.output_lines) > 1000:
                    self.output_lines = self.output_lines[-500:]
            elif item[0] == 'trace':
                event_type, data = item[1]
                if event_type == 'line':
                    self.output_lines.append(f"Trace: Line {data['line']} executed")
                elif event_type == 'vars':
                    if data:
                        self.output_lines.append("Trace: " + ", ".join(f"{k}={v}" for k, v in data.items()))
                if len(self.output_lines) > 1000:
                    self.output_lines = self.output_lines[-500:]
            elif item[0] == 'clear_output':
                self.output_lines.clear()
            self._redraw()

# ===========================
# ENTRY POINT
# ===========================
if __name__ == "__main__":
    app = AnioxazApp()
    curses.wrapper(app.run)
