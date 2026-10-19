from __future__ import annotations

import re
from pathlib import Path

APP_NAME = "ANIOXAZ"
EXECUTION_TIMEOUT = 10
DEFAULT_ITERATION_CAP = 5
MAX_LOG_LINES = 1000


def strip_code_fence(text: str) -> str:
    """Accept models that ignore the no-Markdown instruction."""
    text = text.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        text = re.sub(r"^" + re.escape(fence) + r"[A-Za-z0-9_.+-]*\s*\n?", "", text)
        text = re.sub(r"\n?" + re.escape(fence) + r"\s*$", "", text)
    return text.strip()


def one_paragraph(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def labeled_section(text: str, label: str) -> str:
    pattern = rf"(?ims)^{re.escape(label)}\s*:\s*(.*?)(?=^[A-Z ]+\s*:|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def detect_language(filename: str | None, hint: str = "") -> str:
    lower = (hint or "").lower()
    probes = (
        ("c++", "cpp"),
        ("cpp", "cpp"),
        ("typescript", "typescript"),
        ("javascript", "javascript"),
        ("node.js", "javascript"),
        ("rust", "rust"),
        ("golang", "go"),
        ("java", "java"),
        ("shell", "shell"),
        ("bash", "shell"),
        ("ruby", "ruby"),
        ("php", "php"),
        ("python", "python"),
    )
    for needle, language in probes:
        if needle in lower:
            return language

    suffix = Path(filename).suffix.lower() if filename else ""
    by_suffix = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".ts": "typescript",
        ".sh": "shell",
        ".bash": "shell",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".pl": "perl",
        ".lua": "lua",
    }
    if suffix in by_suffix:
        return by_suffix[suffix]
    return "python"
