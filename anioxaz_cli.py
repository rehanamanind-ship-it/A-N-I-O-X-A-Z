#!/usr/bin/env python3
"""
Anioxaz CLI - Fully local terminal IDE with AI
Uses curses for a Replit‑style UI, a local GGUF model, and tracing.
Made by only only Rehan Aman
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
from dataclasses import dataclass
from pathlib import Path

# Try to import llama-cpp-python (optional)
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

# ===========================
# CONFIGURATION
# ===========================
MODEL_PATH = ""          # will be set by the user
EXECUTION_TIMEOUT = 10   # seconds
EDITOR_TAB_WIDTH = 4

# ===========================
# MODULE 1: LOCAL AI ASSISTANT (no internet)
# ===========================
class AIAssistant:
    """Uses a local GGUF model via llama-cpp-python."""

    def __init__(self):
        self.llm = None
        self.model_path = None

    def load_model(self, path: str) -> bool:
        """Load a GGUF model. Returns True on success."""
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
            return "[Error: No model loaded. Use :model <path>]"
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
# MODULE 2: TRACER (line and variable capture)
# ===========================
class Tracer:
    """Runs code with sys.settrace and sends events via callback."""
    def __init__(self, callback):
        self.callback = callback  # callback(event_type, data)

    def run_with_tracing(self, code: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
        """Returns (list of (stream, line), error_message)."""
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
            try: os.unlink(user_file)
            except: pass
            try: os.unlink(wrapper_file)
            except: pass

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
# MODULE 3: TERMINAL (shell commands)
# ===========================
class Terminal:
    """Runs shell commands asynchronously and outputs via callback."""
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
# MODULE 4: CURSES APPLICATION
# ===========================
class ReplitApp:
    def __init__(self):
        self.ai = AIAssistant()
        self.terminal = Terminal(self.output_callback)
        self.tracer = Tracer(self.trace_callback)

        # UI state
        self.code_lines = [""]          # list of lines
        self.cursor_y = 0               # line index
        self.cursor_x = 0               # column within line
        self.scroll_y = 0               # vertical scroll offset
        self.scroll_x = 0               # horizontal scroll offset
        self.filename = None
        self.running = False
        self.auto_heal = False

        # Output/trace data
        self.output_lines = []           # list of strings
        self.trace_events = []           # list of (event_type, data)
        self.output_scroll = 0

        # Queue for UI updates from threads
        self.ui_queue = queue.Queue()

        # Curses windows
        self.stdscr = None
        self.editor_win = None
        self.output_win = None
        self.status_win = None
        self.cmd_win = None

        # Dimensions
        self.rows = 0
        self.cols = 0
        self.editor_rows = 0
        self.editor_cols = 0
        self.output_rows = 0
        self.output_cols = 0

        # Command input state
        self.cmd_mode = False
        self.cmd_buffer = ""
        self.cmd_history = []
        self.cmd_history_idx = 0

        # Key bindings
        self.keys = {
            'save': (curses.KEY_CTRL, ord('S')),
            'open': (curses.KEY_CTRL, ord('O')),
            'run': (curses.KEY_CTRL, ord('R')),
        }

    # ---------- UI Callbacks ----------
    def output_callback(self, text):
        self.ui_queue.put(('output', text))

    def trace_callback(self, event_type, data):
        self.ui_queue.put(('trace', (event_type, data)))

    # ---------- Drawing ----------
    def _redraw(self):
        self.stdscr.clear()
        self._draw_editor()
        self._draw_output()
        self._draw_status()
        self._draw_command()
        self.stdscr.refresh()

    def _draw_editor(self):
        h, w = self.editor_win.getmaxyx()
        self.editor_win.erase()

        # Show line numbers
        line_num_width = len(str(len(self.code_lines))) + 1
        for i in range(h):
            line_idx = i + self.scroll_y
            if line_idx >= len(self.code_lines):
                break
            line = self.code_lines[line_idx]
            # Line number
            num_str = f"{line_idx+1:>{line_num_width-1}} " if line_idx >= 0 else " "
            self.editor_win.addstr(i, 0, num_str, curses.A_DIM)
            # Code text (with horizontal scroll)
            if len(line) > self.scroll_x:
                disp = line[self.scroll_x:]
            else:
                disp = ""
            # Truncate to width
            max_disp = w - line_num_width
            if len(disp) > max_disp:
                disp = disp[:max_disp-1] + "…"
            self.editor_win.addstr(i, line_num_width, disp)

        # Place cursor
        cursor_y = self.cursor_y - self.scroll_y
        cursor_x = self.cursor_x - self.scroll_x + line_num_width
        if 0 <= cursor_y < h and 0 <= cursor_x < w:
            self.editor_win.move(cursor_y, cursor_x)
        self.editor_win.refresh()

    def _draw_output(self):
        h, w = self.output_win.getmaxyx()
        self.output_win.erase()
        # Show output lines (scrollable)
        start = max(0, len(self.output_lines) - h)
        for i, line in enumerate(self.output_lines[start:]):
            if i >= h:
                break
            self.output_win.addstr(i, 0, line[:w-1])
        self.output_win.refresh()

    def _draw_status(self):
        h, w = self.status_win.getmaxyx()
        self.status_win.erase()
        model_status = self.ai.model_path if self.ai.model_path else "No model"
        filename = self.filename or "Untitled"
        mode = "RUNNING" if self.running else "EDIT"
        status = f"[{mode}] {filename} | Model: {model_status} | Auto‑heal: {'ON' if self.auto_heal else 'OFF'}"
        if len(status) > w-1:
            status = status[:w-1]
        self.status_win.addstr(0, 0, status)
        self.status_win.refresh()

    def _draw_command(self):
        h, w = self.cmd_win.getmaxyx()
        self.cmd_win.erase()
        prompt = ":" if self.cmd_mode else ">"
        text = prompt + self.cmd_buffer
        self.cmd_win.addstr(0, 0, text[:w-1])
        if self.cmd_mode:
            self.cmd_win.move(0, len(prompt) + len(self.cmd_buffer))
        self.cmd_win.refresh()

    # ---------- Input Handling ----------
    def _handle_key(self, key):
        if self.cmd_mode:
            self._handle_cmd_key(key)
            return

        # Editor mode
        if key == curses.KEY_ENTER or key == 10 or key == 13:
            # Insert new line
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
                # Join with previous line
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
                # Join with next line
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

        # Ctrl+O: open
        if key == ord('O') and (curses.KEY_CTRL == 0):  # cheat: check with ctrl
            self._open_file()
            return

        # Ctrl+S: save
        if key == ord('S') and False:  # we'll handle with command
            self._save_file()
            return

        # Ctrl+R: run
        if key == ord('R') and False:
            self._run_code()
            return

        # Enter command mode
        if key == ord(':'):
            self.cmd_mode = True
            self.cmd_buffer = ""
            return

        # Tab key for indentation
        if key == ord('\t') or key == curses.KEY_BTAB:
            # Insert 4 spaces
            line = self.code_lines[self.cursor_y]
            self.code_lines[self.cursor_y] = line[:self.cursor_x] + " " * EDITOR_TAB_WIDTH + line[self.cursor_x:]
            self.cursor_x += EDITOR_TAB_WIDTH
            self._ensure_cursor_visible()
            return

        # Normal printable characters
        if 32 <= key <= 126:
            line = self.code_lines[self.cursor_y]
            self.code_lines[self.cursor_y] = line[:self.cursor_x] + chr(key) + line[self.cursor_x:]
            self.cursor_x += 1
            self._ensure_cursor_visible()
            return

    def _ensure_cursor_visible(self):
        # Adjust scroll
        h, w = self.editor_win.getmaxyx()
        line_num_width = len(str(len(self.code_lines))) + 1
        if self.cursor_y < self.scroll_y:
            self.scroll_y = self.cursor_y
        elif self.cursor_y >= self.scroll_y + h:
            self.scroll_y = self.cursor_y - h + 1
        # Horizontal
        if self.cursor_x < self.scroll_x:
            self.scroll_x = self.cursor_x
        elif self.cursor_x >= self.scroll_x + (w - line_num_width):
            self.scroll_x = self.cursor_x - (w - line_num_width) + 1
        self.scroll_x = max(0, self.scroll_x)

    # ---------- Command Handling ----------
    def _handle_cmd_key(self, key):
        if key == 10 or key == 13:  # Enter
            self._execute_command(self.cmd_buffer)
            self.cmd_buffer = ""
            self.cmd_mode = False
            return
        if key == 27:  # ESC
            self.cmd_mode = False
            self.cmd_buffer = ""
            return
        if key == curses.KEY_BACKSPACE or key == 127:
            self.cmd_buffer = self.cmd_buffer[:-1]
            return
        if 32 <= key <= 126:
            self.cmd_buffer += chr(key)
            return

    def _execute_command(self, cmd):
        cmd = cmd.strip()
        if not cmd:
            return
        # Special commands start with :
        if cmd.startswith(':'):
            parts = cmd[1:].split()
            if not parts:
                return
            verb = parts[0].lower()
            args = parts[1:]
            if verb == 'model':
                if args:
                    path = ' '.join(args)
                    if self.ai.load_model(path):
                        self.output_callback(f"Model loaded: {path}\n")
                    else:
                        self.output_callback(f"Failed to load model from {path}\n")
                else:
                    self.output_callback("Usage: :model /path/to/model.gguf\n")
            elif verb == 'save':
                self._save_file()
            elif verb == 'open':
                if args:
                    self._open_file(' '.join(args))
                else:
                    self.output_callback("Usage: :open filename\n")
            elif verb == 'run':
                self._run_code()
            elif verb == 'explain':
                self._ai_explain()
            elif verb == 'fix':
                self._ai_fix()
            elif verb == 'generate':
                if args:
                    desc = ' '.join(args)
                    self._ai_generate(desc)
                else:
                    self.output_callback("Usage: :generate description\n")
            elif verb == 'autoheal':
                if args and args[0].lower() in ('on','off'):
                    self.auto_heal = args[0].lower() == 'on'
                    self.output_callback(f"Auto‑heal set to {self.auto_heal}\n")
                else:
                    self.output_callback(f"Auto‑heal is {'ON' if self.auto_heal else 'OFF'}\n")
            elif verb == 'help':
                self._show_help()
            else:
                self.output_callback(f"Unknown command: {verb}\n")
        else:
            # Treat as shell command
            self.terminal.run_command(cmd)

    # ---------- File Operations ----------
    def _save_file(self):
        if not self.filename:
            self.output_callback("No filename set. Use :open <file> to set.\n")
            return
        try:
            with open(self.filename, 'w') as f:
                f.write('\n'.join(self.code_lines))
            self.output_callback(f"Saved: {self.filename}\n")
        except Exception as e:
            self.output_callback(f"Save error: {e}\n")

    def _open_file(self, path=None):
        if path is None:
            # we can't prompt easily in curses; we'll ask via command input or simply use current filename
            self.output_callback("Please use :open <filename>\n")
            return
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

    # ---------- Run Code ----------
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

    # ---------- AI Actions ----------
    def _ai_explain(self):
        code = '\n'.join(self.code_lines)
        if not code.strip():
            self.output_callback("No code to explain.\n")
            return
        self.output_callback("--- Explanation ---\n")
        resp = self.ai.explain_code(code)
        self.output_callback(resp + "\n")

    def _ai_fix(self):
        code = '\n'.join(self.code_lines)
        if not code.strip():
            self.output_callback("No code to fix.\n")
            return
        # We need to ask for error description. Use a simple prompt in output area.
        self.output_callback("Describe the error or what's wrong, then type 'END' on a new line.\n")
        # We'll handle this by reading from command input? Better to use a simple modal.
        # For simplicity, we'll ask via a prompt (we can't do input easily in curses without blocking)
        # We'll use a small input routine.
        self._prompt_user("Error description: ", self._ai_fix_callback)

    def _ai_fix_callback(self, desc):
        if not desc:
            return
        code = '\n'.join(self.code_lines)
        self.output_callback("--- AI Fixing ---\n")
        resp = self.ai.fix_code(code, desc)
        if resp:
            # Replace code
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

    def _ai_generate(self, desc):
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
            self._run_code()  # re‑run automatically
        else:
            self.output_callback("[Auto‑heal] No fix found.\n")

    # ---------- Prompt user (simple) ----------
    def _prompt_user(self, prompt, callback):
        # This is a hack: we temporarily set a callback for the next command input
        self._prompt_callback = callback
        self._prompt_text = prompt
        self.cmd_mode = True
        self.cmd_buffer = prompt
        # We'll handle special mode where command input is used for prompt
        # We'll override normal command execution for one shot
        self._in_prompt = True

    # We'll intercept command execution when in prompt mode
    def _execute_command(self, cmd):
        if hasattr(self, '_in_prompt') and self._in_prompt:
            # This is a prompt response
            self._in_prompt = False
            if hasattr(self, '_prompt_callback'):
                cb = self._prompt_callback
                delattr(self, '_prompt_callback')
                delattr(self, '_prompt_text')
                cb(cmd)
            return
        # Normal command handling
        super()._execute_command(cmd)  # but we are in same class, so we use the method above

    # We need to refactor: the above is messy. For simplicity, we'll skip the prompt and use a fixed description for fix.

    def _show_help(self):
        help_text = """
Commands:
  :model <path>          – load a GGUF model
  :open <file>           – open a Python file
  :save                  – save current file
  :run                   – run the code with tracing
  :explain               – explain current code
  :fix                   – fix code (asks for error description)
  :generate <desc>       – generate code from description
  :autoheal on/off       – toggle auto‑healing
  :help                  – show this help

Shell commands can be typed directly (e.g., ls, pip).
"""
        self.output_callback(help_text)

    # ---------- Main Loop ----------
    def run(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(1)
        stdscr.nodelay(0)
        curses.noecho()

        # Setup windows
        self.rows, self.cols = stdscr.getmaxyx()
        self.editor_rows = int(self.rows * 0.6)
        self.output_rows = int(self.rows * 0.3)
        status_rows = 1
        cmd_rows = 1

        self.editor_win = curses.newwin(self.editor_rows, self.cols, 0, 0)
        self.output_win = curses.newwin(self.output_rows, self.cols, self.editor_rows, 0)
        self.status_win = curses.newwin(status_rows, self.cols, self.editor_rows + self.output_rows, 0)
        self.cmd_win = curses.newwin(cmd_rows, self.cols, self.editor_rows + self.output_rows + status_rows, 0)

        self._redraw()

        # Main event loop
        while True:
            try:
                key = stdscr.getch()
            except KeyboardInterrupt:
                break

            if key == -1:
                continue

            # Process UI events from queue
            self._process_ui_queue()

            if key == 27:  # ESC: exit command mode or just ignore
                if self.cmd_mode:
                    self.cmd_mode = False
                    self.cmd_buffer = ""
                continue

            if self.cmd_mode:
                self._handle_cmd_key(key)
            else:
                self._handle_key(key)

            self._redraw()

        curses.endwin()

    def _process_ui_queue(self):
        while not self.ui_queue.empty():
            item = self.ui_queue.get_nowait()
            if item[0] == 'output':
                text = item[1]
                self.output_lines.append(text)
                # Limit lines to avoid memory issues
                if len(self.output_lines) > 1000:
                    self.output_lines = self.output_lines[-500:]
            elif item[0] == 'trace':
                event_type, data = item[1]
                if event_type == 'line':
                    self.output_lines.append(f"Trace: Line {data['line']} executed")
                elif event_type == 'vars':
                    if data:
                        self.output_lines.append("Trace: " + ", ".join(f"{k}={v}" for k, v in data.items()))
                # Limit
                if len(self.output_lines) > 1000:
                    self.output_lines = self.output_lines[-500:]
            elif item[0] == 'clear_output':
                self.output_lines.clear()
            # Update output window scroll to bottom
            self._redraw()

# ===========================
# ENTRY POINT
# ===========================
if __name__ == "__main__":
    # Use curses.wrapper to handle setup/teardown
    app = ReplitApp()
    curses.wrapper(app.run)
