from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

try:
    from llama_cpp import Llama
except ImportError:  # pragma: no cover - optional dependency
    Llama = None

from .core import strip_code_fence, one_paragraph, labeled_section


class LocalModel:
    """A locally loaded GGUF model with a role-specific public interface."""

    def __init__(self, role: str) -> None:
        self.role = role
        self.llm = None
        self.model_path: Optional[str] = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self.llm is not None

    @property
    def name(self) -> str:
        return Path(self.model_path).name if self.model_path else "not loaded"

    def load(self, path: str) -> tuple[bool, str]:
        path = path.strip()
        if not path:
            return False, "Choose a local GGUF model path."
        if not Path(path).is_file():
            return False, f"Model file was not found: {path}"
        if Llama is None:
            return False, "llama-cpp-python is not installed."
        try:
            with self._lock:
                self.llm = Llama(
                    model_path=path,
                    n_ctx=4096,
                    n_threads=max(1, (os.cpu_count() or 2) - 1),
                    verbose=False,
                )
                self.model_path = path
            return True, f"{self.role.title()} model loaded: {Path(path).name}"
        except Exception as exc:
            self.llm = None
            self.model_path = None
            return False, f"Could not load {self.role} model: {exc}"

    def complete(self, user: str, system: str, max_tokens: int = 2048) -> str:
        if not self.loaded:
            raise RuntimeError(f"No {self.role} model is loaded.")
        messages = []
        if system.strip():
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        try:
            with self._lock:
                reply = self.llm.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.2,
                )
            return reply["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise RuntimeError(f"{self.role.title()} model error: {exc}") from exc


class Architect(LocalModel):
    """Planner, interpreter, and user-facing narrator. Never writes code."""

    SYSTEM = """You are the ANIOXAZ Architect, an offline software planner.
Never write production code. Create concise, language-aware implementation
plans covering modules/functions, inputs, outputs, dependencies, edge cases,
and success criteria. You are the only model that speaks to the user.
When an execution failure is supplied, classify it as ARCHITECTURE or CODE.
Explain it in plain language and never reveal raw stack traces to the user."""

    def plan(self, request: str, philosophy: str, source: str = "") -> str:
        system = self.SYSTEM
        if philosophy.strip():
            system += "\n\nPersistent Philosophy File:\n" + philosophy.strip()
        user = "User request:\n" + request
        if source.strip():
            user += "\n\nCurrent implementation for review:\n" + source
        return self.complete(user, system, 2400)

    def diagnose(
        self, plan: str, raw_error: str, previous_instruction: str
    ) -> tuple[str, str, str]:
        system = self.SYSTEM + """

Return exactly three labeled sections:
CLASSIFICATION: ARCHITECTURE or CODE
USER: one simple paragraph explaining the failure and next step, with no raw
traceback or compiler diagnostic.
CODER: a self-contained repair instruction. Do not quote the raw error. Use a
materially different strategy than the previous repair instruction."""
        user = (
            f"Plan:\n{plan}\n\n"
            f"Architect-only raw diagnostic:\n{raw_error}\n\n"
            f"Previous repair instruction:\n{previous_instruction or '(none)'}"
        )
        response = self.complete(user, system, 1800)
        classification = "ARCHITECTURE" if "ARCHITECTURE" in response.upper() else "CODE"
        explanation = labeled_section(response, "USER") or (
            "The implementation did not complete successfully, so I am revising it."
        )
        instruction = labeled_section(response, "CODER") or (
            "Review the current implementation and apply a safe correction."
        )
        return classification, one_paragraph(explanation), instruction

    def summarize(self, request: str, output: str, philosophy: str) -> str:
        system = self.SYSTEM
        if philosophy.strip():
            system += "\n\nPersistent Philosophy File:\n" + philosophy.strip()
        user = (
            "The task completed. Summarize the result for the user in one plain "
            "language paragraph, without code.\n\n"
            f"Request:\n{request}\n\nProgram output:\n{output or '(no output)'}"
        )
        return one_paragraph(self.complete(user, system, 500))

    def explain(self, source: str, philosophy: str) -> str:
        system = self.SYSTEM
        if philosophy.strip():
            system += "\n\nPersistent Philosophy File:\n" + philosophy.strip()
        return self.complete(
            "Explain this code clearly without rewriting it:\n\n" + source,
            system,
            1200,
        )

    def translate_error(self, raw_error: str) -> str:
        return one_paragraph(
            self.complete(
                "Turn this execution error into one plain-language paragraph. "
                "Do not include raw error text or a traceback. Explain the next "
                "sensible step.\n\n" + raw_error,
                self.SYSTEM,
                500,
            )
        )


class Coder(LocalModel):
    """Code-only model. In dual mode it never receives philosophy or user prose."""

    SYSTEM = """You are the ANIOXAZ Coder. Return source code only, without
Markdown fences, explanations, or questions. Follow the Architect's plan.
You never communicate with the user."""

    def from_plan(self, plan: str, existing: str = "") -> str:
        prompt = "Architectural plan:\n" + plan
        if existing.strip():
            prompt += "\n\nExisting implementation:\n" + existing
        return strip_code_fence(self.complete(prompt, self.SYSTEM, 4096))

    def repair(self, instruction: str, source: str) -> str:
        prompt = (
            "Architect repair instruction:\n"
            + instruction
            + "\n\nCurrent implementation:\n"
            + source
        )
        return strip_code_fence(self.complete(prompt, self.SYSTEM, 4096))

    def fallback(self, request: str, existing: str = "") -> str:
        prompt = "User request in fallback mode:\n" + request
        if existing.strip():
            prompt += "\n\nCurrent implementation:\n" + existing
        return strip_code_fence(self.complete(prompt, self.SYSTEM, 4096))

    def fallback_repair(self, source: str, raw_error: str) -> str:
        prompt = (
            "Repair this implementation. Return corrected code only.\n\n"
            f"Current implementation:\n{source}\n\nRaw diagnostic:\n{raw_error}"
        )
        return strip_code_fence(self.complete(prompt, self.SYSTEM, 4096))
