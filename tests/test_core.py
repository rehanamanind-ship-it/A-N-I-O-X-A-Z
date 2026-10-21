from anioxaz import __version__
from anioxaz.core import detect_language, strip_code_fence


def test_version_is_1_0_1():
    assert __version__ == "1.0.1"


def test_strip_code_fence_removes_markdown_wrappers():
    raw = "```python\nprint('hi')\n```"
    assert strip_code_fence(raw) == "print('hi')"


def test_detect_language_from_suffix_and_hint():
    assert detect_language("script.py") == "python"
    assert detect_language("main.js") == "javascript"
    assert detect_language("main.c", "C++ project") == "cpp"
