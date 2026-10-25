import threading

from anioxaz.app import AnioxazApp
from anioxaz.editor import EditorScreen
from anioxaz.executor import CodeExecutor, Terminal
from anioxaz.models import Architect, Coder


def test_load_model_rejects_missing_model_file():
    architect = Architect("architect")
    success, message = architect.load("/tmp/anioxaz-model-does-not-exist.gguf")
    assert success is False
    assert "not found" in message


def test_run_pipeline_interface_is_available():
    app = AnioxazApp()
    assert callable(app.run_pipeline)


def test_append_log_keeps_application_history_bounded():
    app = AnioxazApp()
    app.append_log("first message")
    assert app.output_history[-1] == "first message"
    assert len(app.output_history) <= 1000


def test_CodeExecutor_runs_python_source():
    executor = CodeExecutor(lambda event, data: None)
    result = executor.run("print('ok')", "python")
    assert result.error is None
    assert result.stdout.strip() == "ok"


def test_EditorScreen_and_Philosophy_interfaces_exist():
    app = AnioxazApp()
    assert issubclass(EditorScreen, object)
    assert app.philosophy_text == ""
    assert callable(app.open_philosophy_menu)
    assert Coder.SYSTEM


def test_Terminal_runs_a_local_command():
    messages = []
    finished = threading.Event()

    def collect(message: str) -> None:
        messages.append(message)
        if message.startswith("[Shell finished"):
            finished.set()

    terminal = Terminal(collect)
    terminal.run_command("printf terminal-ok")
    assert finished.wait(5)
    assert any("terminal-ok" in message for message in messages)


def test_AutoHeal_state_is_disabled_by_default():
    app = AnioxazApp()
    assert app.auto_heal is False
    assert callable(app.toggle_auto_heal)
