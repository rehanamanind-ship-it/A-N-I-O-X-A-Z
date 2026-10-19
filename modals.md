models.md – ANIOXAZ Dual‑Model Architecture Specification (Textual Edition)

Author: Rehan Aman
Target project: ANIOXAZ (anioxaz_cli.py)
Framework: Textual (Python TUI framework by Textualize)
Audience: GitHub Copilot (or any AI coding assistant implementing this feature)
📌 Purpose of this Document

This file describes what the ANIOXAZ dual‑model system must do and how it should behave – not how to code it. The implementing AI must design the actual code itself while respecting every rule here.

The app is built with Textual, not curses. The whole experience must be fully offline, language‑agnostic, non‑intrusive to existing functionality, as user‑friendly as possible, and visually beautiful – using Textual's widgets, CSS, Rich rendering, and animations to deliver real terminal flair.
🎯 Feature Summary

The user gains a two‑model pipeline:

    One model acts as the Architect (planner, decision‑maker, error interpreter).

    One model acts as the Coder (code writer and code fixer).

The user only ever speaks to the Architect when both are loaded.
The Coder never speaks to the user – only to the Architect.
Errors are never shown raw to the user – the Architect always translates them into plain language first.

If the Architect is missing, the system falls back to sending the user's prompt directly to the Coder.
If neither model is loaded, the system refuses and reports an error.

Additionally:

    The user can supply a Philosophy File (markdown) as a persistent system prompt for the Architect.

    The prompt area must be large, multi‑line, and reusable.

    The editor must be nano‑style capable and can lean on Textual's TextArea widget for the heavy lifting.

    ANIOXAZ must feel like a first‑class Textual app: CSS‑styled, animated, cohesive, branded.

🏛️ Roles
Architect Model

Responsibilities:

    Receive the user's request in natural language.

    Receive and honour the Philosophy File (if one is loaded).

    Produce a complete architectural plan.

    Pass that plan to the Coder.

    Receive errors from execution.

    Decide whether the fault lies in the architecture or in the code.

    Either revise the architecture or instruct the Coder to fix the code.

    Explain to the user, in simple language, what went wrong and what it is doing about it.

    Decide when the task is complete.

    Ask the user for clarification only when genuinely necessary.

The Architect must never write production code.
Coder Model

Responsibilities:

    Receive only the architectural plan (never the raw user prompt) when the Architect is present.

    Receive the user prompt directly when the Architect is absent (fallback mode).

    Produce code in the language the user requested.

    Receive fix instructions from the Architect and rewrite/fix the code accordingly.

    Output code only – no explanations directed at the user.

The Coder must never ask the user anything.
The Coder must never bypass the Architect when the Architect is present.
The Coder must never receive the Philosophy File – it belongs to the Architect alone.
📖 Philosophy File (System Prompt for the Architect)
Purpose

A Philosophy File is a plain markdown document written (or edited) by the user. It describes how the Architect should think, prioritise, and behave. It is the Architect's permanent personality layer.
Examples of what it can contain

    Coding standards and style preferences.

    Priorities (e.g., "readability over performance").

    Architectural preferences (e.g., "prefer functional composition").

    Naming conventions.

    Error‑handling philosophy.

    Preferred libraries or frameworks.

    What to avoid.

    Tone and language to use with the user.

Rules

    The user can create a new Philosophy File or load an existing one from the menu.

    The Philosophy File is entirely optional. If none is loaded, the Architect behaves normally.

    The content of the Philosophy File is prepended to every prompt sent to the Architect – as a system‑level instruction.

    The Philosophy File is never sent to the Coder – only to the Architect.

    The Philosophy File persists for the entire session until the user changes or clears it.

    The user must be able to view, edit, replace, and clear the Philosophy File from the menu.

Where it is stored

    Any path chosen by the user.

    Default extension: .md.

    The user may keep multiple Philosophy Files and switch between them.

🔁 Control Flow
Normal Mode (both models loaded)

    User submits a request in the large multi‑line prompt.

    Architect receives:

        The Philosophy File (if loaded).

        The user request.
        It produces an architecture plan covering modules, functions, inputs, outputs, dependencies, edge cases, and success criteria.

    Coder receives the plan and produces code in the requested language.

    Code is executed through the existing execution/tracing pipeline.

    On success, the Architect summarises the outcome to the user.

    On failure, the raw error goes to the Architect only.

    Architect diagnoses and decides:

        ARCHITECTURE issue → revise plan, hand to Coder.

        CODE issue → instruct Coder to fix its own code.

    Coder produces updated code. Execution re‑runs.

    Loop repeats until success, iteration cap (default 5, configurable), or the Architect needs user input.

Fallback Mode (only Coder loaded)

    Prompt goes straight to the Coder.

    Coder produces and fixes code directly.

    Philosophy File is ignored.

    Loop repeats until success or iteration cap.

Error Mode (no models loaded)

    Pipeline refuses to run.

    Clear message that at least one model must be loaded.

🧠 Decision Rules for the Architect

    Always classify failures as ARCHITECTURE or CODE first.

    Always produce a single‑paragraph explanation in simple language for the user.

    Never repeat the same fix twice in a row – switch strategy instead.

    Ask the user only when genuinely necessary.

    Honour the Philosophy File when it doesn't conflict with correctness.

🗣️ Conversation Rules

    User ↔ Architect: allowed (normal mode).

    User ↔ Coder: allowed only in fallback mode.

    Architect ↔ Coder: allowed when both present.

    Coder → User: forbidden.

🌍 Language Agnosticism

    Support any language the Coder model can produce (Python, JS, Rust, Go, C, C++, Java, shell, etc.).

    The Architect respects the user's chosen language when writing the plan.

    The executor must delegate to the host's interpreter/compiler for supported languages, or clearly inform the user when a language can't be executed on this machine while still producing the code.

    Nothing in the pipeline may assume Python.

✍️ Large, Multi‑Line Prompt Area

The prompt must not be a single line. It must be a Textual TextArea widget (or equivalent) with the following properties:

    Multi‑line, resizable, minimum 6 visible lines, growing to 8–10 on taller terminals.

    Word wrap enabled.

    Enter inserts a newline, Ctrl+Enter (or a bound submit key) submits – clearly labelled in the hint bar.

    Own bordered container with a PROMPT title, distinct colour, and visible focus indicator.

    Internal scrolling when content exceeds height.

    Full editing – arrows, Home/End, Page Up/Down, Backspace, Delete.

    Reusable component for: Build request, Fix description, Generate description, Philosophy File editing, and any future input.

    ESC cancels, submit key sends – both must be obvious in the UI.

📝 Editor (Nano‑Style)

The editor is built on Textual's TextArea widget (or an equivalent custom widget). It must support:
Core Editing

    Insert, delete, newline, auto‑indent, Tab / Shift+Tab, smart Home / End, word navigation, page scroll, Ctrl+Home / Ctrl+End, undo/redo.

Selection & Clipboard

    Shift+Arrows, Ctrl+A, Ctrl+C/X/V, Ctrl+K / Ctrl+U (nano‑style line cut/paste), Ctrl+Shift+K (delete line). Internal clipboard.

Search & Replace

    Ctrl+F / Ctrl+W to search, F3 / Shift+F3 for next/previous, Ctrl+H for replace with "replace all" safety, case‑sensitive toggle.

File Operations

    Ctrl+S save, Ctrl+O open, Ctrl+Shift+S save as, Alt+N new buffer, Ctrl+W close buffer (prompt to save if dirty).

    Dirty indicator (●) next to the filename in the tab strip and status.

Multi‑Buffer

    Multiple files open simultaneously with a tab strip at the top of the editor panel (Textual Tabs widget is ideal).

    Ctrl+Page Up/Down or Alt+1..9 to switch.

    Closing the last tab returns to the main menu.

Line Numbers, Gutter, Status

    Line numbers, current line highlight, Ln X, Col Y in the editor status strip, dirty indicator, language hint.

Navigation Aids

    Go to line (Ctrl+G), bracket matching, indent guides, trailing whitespace highlighting, word wrap toggle (Alt+Z).

Undo/Redo

    Per buffer, coalescing consecutive typing, redo cleared on new edits.

Keyboard Shortcuts (must all work)
Key	Action
Arrows / Shift+Arrows	Move / extend selection
Ctrl+Arrows	Word movement
Home / End	Smart line start/end
Ctrl+Home / Ctrl+End	File start/end
Page Up / Page Down	Screen scroll
Enter	Newline with auto‑indent
Tab / Shift+Tab	Indent / unindent
Ctrl+Z / Ctrl+Y	Undo / redo
Ctrl+A / C / X / V	Select all / copy / cut / paste
Ctrl+K / Ctrl+U	Cut line / paste line
Ctrl+F / Ctrl+W	Search
Ctrl+H	Replace
F3 / Shift+F3	Next / previous match
Ctrl+G	Go to line
Ctrl+S / Ctrl+O / Ctrl+Shift+S	Save / open / save as
Alt+N	New buffer
Alt+Z	Toggle word wrap
Ctrl+Page Up/Down	Switch buffer
ESC	Back to menu

Bindings must be documented inside the app (Help → Editor and hint bar).
Integration

    The same editor widget is reused for editing the Philosophy File.

    The editor stays responsive while the pipeline runs.

    ESC never silently loses unsaved changes.

    Uses Textual's reactive model so status updates propagate automatically.

🎨 ANIOXAZ Visual Identity (Textual Edition)

Textual gives us far more than curses: CSS styling, Rich markup, animations, reactive state, and first‑class widgets. ANIOXAZ must use these to look genuinely beautiful.
Brand

    Name: ANIOXAZ – always rendered in uppercase, styled and consistent.

    Banner: a large ANIOXAZ banner at the top of the main screen, rendered with Rich/Textual markup – bold, gradient or accent colour, aligned.

    Tagline: optional subtle line below (e.g., offline · local · yours) in a muted style.

Design System

    CSS‑driven styling

        All visual styling lives in a Textual CSS file (or an inline CSS block), not hard‑coded in widget code.

        A single CSS file defines the palette, spacing, borders, and states.

        Widgets use classes and IDs for styling – no ad‑hoc inline styles.

    Palette

        primary – banner, active elements

        accent – highlights, focus

        success – green

        warning – yellow

        error – red

        info – cyan/blue

        muted – dim grey for secondary text

        surface – panel background

        surface-alt – secondary panel background

        The same colour always means the same thing.

    Borders and structure

        Every panel uses a Textual border with a border-title rendered inside the top border.

        Border styles: rounded for main panels, heavy for modal focus, solid for secondary.

        Panels are separated by consistent padding – never touching.

    Typography

        Bold for headings and selected items.

        Dim for line numbers, hints, and metadata.

        Reverse / highlighted style for the focused panel's title.

        Never mix more than three weights at once.

    Icons and glyphs

        Unicode symbols: ▶, ●, ✓, ✗, ⚠, ⟳, ▸, ▾.

        Fall back to ASCII if the terminal lacks Unicode.

        Icons must never break layout.

    Layout rhythm across all screens

        Header – banner (main screen) or compact header with screen name.

        Body – menu, editor, or prompt.

        Footer – status bar + key hints.

        The same rhythm everywhere → feels like one app.

    Status bar

        Persistent Textual Footer‑like bar.

        Shows: mode, file, loaded models, auto‑heal state, iteration count if running.

        Colour‑coded states: idle / thinking / running / error.

    Hint bar

        A second line under the status bar showing relevant key bindings for the current screen.

        Main menu: ↑↓ navigate · Enter select · Tab editor

        Editor: ESC back · Ctrl+S save · Ctrl+F search

        Prompt: Enter newline · Ctrl+Enter submit · ESC cancel

        No guessing.

    Smooth transitions

        Use Textual's screen stack for navigation.

        Use push_screen / pop_screen for clean transitions.

        No flicker – Textual handles the redraw.

    Feedback everywhere

        Loading a model → toast or status message.

        Running code → status shows Running… with an animated spinner (Textual LoadingIndicator).

        AI thinking → status shows dots or a spinner.

        Errors → toast notifications + red status bar + message in the log.

    Empty states

        Empty editor → # Start typing your code here.

        Empty output → (no output yet).

        No model → ⚠ No model loaded — open Model menu.

    Graceful degradation

        No colour → still structured via borders and weight.

        No Unicode → ASCII fallbacks everywhere.

        Small terminal → responsive layout that hides the banner and shrinks panels.

    No visual noise

        No random colour changes.

        No blinking text.

        No unnecessary animations.

        Every visual element serves a purpose.

    Respect the eyes

        No pure white on pure black unless the terminal forces it.

        Prefer softer foreground colours when 256‑colour / truecolor is available.

        Avoid red on dark red, yellow on light, etc.

Suggested Textual Widgets

    Header / Footer – for status and key hints.

    Tree or ListView – for the vertical menu.

    TextArea – for the editor and the prompt.

    Tabs – for multi‑buffer editing.

    RichLog – for the output pane (supports Rich markup, scrolling, and styled lines).

    Input – for short single‑line prompts (filenames, paths).

    ModalScreen – for confirmations and settings.

    LoadingIndicator – during AI calls and code execution.

    Toast / notify() – for lightweight notifications.

    ProgressBar – optional for long model loads.

    Markdown widget – to render the Philosophy File preview if desired.

Screen‑by‑Screen Reference

Main Menu
text

╭──────────────── ANIOXAZ ────────────────╮
│  █████  ███   ██ ██  ██████  ██  ██ ... │
│                                         │
│  ▶ Editor          │  (output pane)    │
│    Build           │                    │
│    Run             │                    │
│    Explain         │                    │
│    Generate        │                    │
│    File            │                    │
│    Model           │                    │
│    Philosophy      │                    │
│    Shell           │                    │
│    AutoHeal        │                    │
│    Help            │                    │
│    Exit            │                    │
╰─────────────────────────────────────────╯
╭────────── STATUS ──────────────────────╮
│ Ready · no file · no model · autoheal OFF │
╰────────────────────────────────────────╯
 ↑↓ navigate · Enter select · Tab editor

Editor
text

╭────────── EDITOR — my_script.py ● ──────╮
│ 1  # Write your code here               │
│ 2  def main():                          │
│ 3      print("hello")                   │
╰─────────────────────────────────────────╯
╭────────── OUTPUT ──────────────────────╮
│ (no output yet)                         │
╰─────────────────────────────────────────╯
╭────────── STATUS ──────────────────────╮
│ Editing · my_script.py · Ln 3 Col 5     │
╰────────────────────────────────────────╯
 ESC back · Ctrl+S save · Ctrl+F search

Prompt
text

╭────────── PROMPT — what to build? ──────╮
│ write a python script that reads        │
│ sales.csv and prints monthly totals      │
│                                          │
│                                          │
╰─────────────────────────────────────────╯
╭────────── STATUS ──────────────────────╮
│ Waiting for input                       │
╰────────────────────────────────────────╯
 Enter newline · Ctrl+Enter submit · ESC cancel

Every ANIOXAZ screen follows the same rhythm: header → panels → status → hints.
🧱 Interaction with Existing Features

    All existing menu items, shell, file operations, tracing, and single‑model commands must continue to work unchanged.

    The new pipeline is additional, not a replacement.

    The pipeline runs in the background so the UI stays responsive (use Textual workers).

    Progress is visible in the output pane in plain language.

    The iteration cap defaults to 5 and is configurable.

    The multi‑line prompt replaces the old single‑line prompt where appropriate; short single‑line prompts (filenames, paths) can still use Input.

    The Philosophy File feature slots in cleanly.

    The editor upgrade must be backwards compatible with the existing editor menu entry.

🛡️ Safeguards

    No model loaded → pipeline refuses, clear message.

    Only Coder → fallback mode, Philosophy ignored.

    Only Architect → pipeline refuses, user told Coder is missing.

    Iteration cap reached → stop, honest summary.

    Coder never exposed as a menu label.

    Philosophy File never sent to Coder.

    No network calls, no external APIs. Fully offline.

    No removal or renaming of existing functionality.

    Small terminals → reduced prompt height, never crash.

✅ Success Criteria

ANIOXAZ is complete when:

    Built with Textual and runnable via python anioxaz_cli.py.

    All styling is CSS‑driven – no ad‑hoc inline styles.

    ANIOXAZ branding – banner, tagline, consistent palette.

    Menu, editor, prompt, output, status, hints – all present and styled.

    Multi‑line prompt with all specified behaviour.

    Nano‑style editor with all specified shortcuts working.

    Multi‑buffer editing with tab strip.

    Philosophy File can be created, loaded, viewed, edited, replaced, cleared.

    Dual‑model pipeline works in normal, fallback, and error modes.

    Errors are always translated by the Architect (or clearly labelled raw in fallback).

    Iteration cap stops the loop cleanly.

    Every prior feature still works.

    Load, think, run, error states all show clear Textual feedback.

    Degrades gracefully without colour, without Unicode, on small terminals.

    Looks and feels like a polished Textual app – not a curses port.

End of ANIOXAZ specification (Textual Edition).
The implementing AI must design the code itself, using Textual as the TUI framework, respecting all rules above, without assuming Python as the only target language for generated code, without introducing any external editor dependency, and delivering genuine terminal flair.