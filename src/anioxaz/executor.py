from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .core import EXECUTION_TIMEOUT


@dataclass
class ExecutionResult:
    stdout: str = ""
    error: Optional[str] = None
    language: str = "python"
    phase: str = "run"


class Tracer:
    """Python variable and line tracing, filtered strictly to user source."""

    def __init__(self, callback: Callable[[str, dict], None]) -> None:
        self.callback = callback

    def run(self, code: str, timeout: int = EXECUTION_TIMEOUT) -> ExecutionResult:
        with tempfile.TemporaryDirectory(prefix="anioxaz-") as temporary:
            folder = Path(temporary)
            source = folder / "program.py"
            source.write_text(code, encoding="utf-8")
            runner = folder / "trace_runner.py"
            runner.write_text(
                """
import json
import runpy
import sys

target = sys.argv[1]
def trace(frame, event, arg):
    if event == "line" and frame.f_code.co_filename == target:
        print("ANIOXAZ_LINE:" + str(frame.f_lineno), file=sys.stderr)
        values = {key: repr(value)[:200] for key, value in frame.f_locals.items()
                  if not key.startswith("__")}
        print("ANIOXAZ_VARS:" + json.dumps(values), file=sys.stderr)
    return trace

sys.settrace(trace)
runpy.run_path(target, run_name="__main__")
""".strip(),
                encoding="utf-8",
            )
            try:
                completed = subprocess.run(
                    [sys.executable, str(runner), str(source)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=folder,
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    error=f"Execution timed out after {timeout} seconds.",
                    language="python",
                )
            actual_stderr: list[str] = []
            for line in completed.stderr.splitlines():
                if line.startswith("ANIOXAZ_LINE:"):
                    self.callback("line", {"line": line.partition(":")[2]})
                elif line.startswith("ANIOXAZ_VARS:"):
                    try:
                        self.callback(
                            "vars", json.loads(line.partition(":")[2].strip())
                        )
                    except json.JSONDecodeError:
                        pass
                else:
                    actual_stderr.append(line)
            error = None
            if completed.returncode:
                error = "\n".join(actual_stderr).strip() or (
                    f"Python exited with code {completed.returncode}."
                )
            return ExecutionResult(completed.stdout, error, "python")


class CodeExecutor:
    """Delegate execution to local interpreters or compilers when available."""

    EXTENSIONS = {
        "javascript": ".js",
        "typescript": ".ts",
        "shell": ".sh",
        "go": ".go",
        "rust": ".rs",
        "c": ".c",
        "cpp": ".cpp",
        "java": ".java",
        "ruby": ".rb",
        "php": ".php",
        "perl": ".pl",
        "lua": ".lua",
    }

    def __init__(self, trace_callback: Callable[[str, dict], None]) -> None:
        self.tracer = Tracer(trace_callback)

    def run(self, source: str, language: str) -> ExecutionResult:
        language = language.lower()
        if language == "python":
            return self.tracer.run(source)
        extension = self.EXTENSIONS.get(language)
        if extension is None:
            return ExecutionResult(
                error=f"No local runner is configured for {language}.",
                language=language,
                phase="prepare",
            )
        with tempfile.TemporaryDirectory(prefix="anioxaz-") as temporary:
            folder = Path(temporary)
            path = folder / ("Main.java" if language == "java" else "program" + extension)
            path.write_text(source, encoding="utf-8")
            command, failure, phase = self._command(language, path, folder)
            if failure:
                return ExecutionResult(error=failure, language=language, phase=phase)
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=EXECUTION_TIMEOUT,
                    cwd=folder,
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    error=f"Execution timed out after {EXECUTION_TIMEOUT} seconds.",
                    language=language,
                )
            error = None
            if completed.returncode:
                error = completed.stderr.strip() or (
                    f"{language.title()} exited with code {completed.returncode}."
                )
            return ExecutionResult(completed.stdout, error, language)

    def _command(
        self, language: str, source: Path, folder: Path
    ) -> tuple[list[str], Optional[str], str]:
        programs = {
            "javascript": "node",
            "typescript": "tsx",
            "shell": "bash",
            "go": "go",
            "rust": "rustc",
            "c": "gcc",
            "cpp": "g++",
            "java": "javac",
            "ruby": "ruby",
            "php": "php",
            "perl": "perl",
            "lua": "lua",
        }
        program = programs[language]
        if not shutil.which(program):
            return [], (
                f"This machine cannot run {language}: '{program}' is not on PATH. "
                "The generated code remains in the editor."
            ), "prepare"
        if language in {"javascript", "typescript", "shell", "ruby", "php", "perl", "lua"}:
            return [program, str(source)], None, "run"
        if language == "go":
            return ["go", "run", str(source)], None, "run"
        if language in {"rust", "c", "cpp"}:
            binary = folder / "anioxaz_program"
            compiler_commands = {
                "rust": ["rustc", str(source), "-o", str(binary)],
                "c": ["gcc", str(source), "-o", str(binary)],
                "cpp": ["g++", str(source), "-o", str(binary)],
            }
            compile_result = subprocess.run(
                compiler_commands[language],
                capture_output=True,
                text=True,
                cwd=folder,
            )
            if compile_result.returncode:
                return [], compile_result.stderr.strip() or "Compilation failed.", "compile"
            return [str(binary)], None, "run"
        compile_result = subprocess.run(
            ["javac", str(source)],
            capture_output=True,
            text=True,
            cwd=folder,
        )
        if compile_result.returncode:
            return [], compile_result.stderr.strip() or "Java compilation failed.", "compile"
        return ["java", "-cp", str(folder), "Main"], None, "run"


class Terminal:
    """Original shell command feature, moved off the Textual UI thread."""

    def __init__(self, output: Callable[[str], None]) -> None:
        self.output = output
        self.process: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()

    def run_command(self, command: str) -> None:
        if not command.strip():
            return

        def target() -> None:
            self.output(f"$ {command}")
            try:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                with self.lock:
                    self.process = process
                assert process.stdout is not None
                for line in iter(process.stdout.readline, ""):
                    self.output(line.rstrip("\n"))
                process.stdout.close()
                process.wait()
                self.output(f"[Shell finished with code {process.returncode}]")
            except Exception as exc:
                self.output(f"Shell error: {exc}")
            finally:
                with self.lock:
                    self.process = None

        threading.Thread(target=target, daemon=True).start()

    def stop(self) -> bool:
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                return False
            self.process.terminate()
            return True
