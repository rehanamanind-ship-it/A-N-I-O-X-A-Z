anioxaz_cli – Offline Terminal IDE with Local AI

Author: Rehan Aman
🧠 What is this?

anioxaz_cli is a fully offline, menu‑driven coding environment that runs entirely in your terminal. It combines a code editor, a Python executor with live tracing, an integrated shell, and a local AI assistant powered by a GGUF model of your choice.

No internet, no subscriptions, no telemetry – just you, your terminal, and your code.
✨ Features

    Vertical menu – navigate with ↑/↓, select with Enter.

    Code editor – appears only when you select it from the menu. Full editing (arrow keys, Home/End, Page Up/Down, Tab indentation).

    Live execution tracing – see each line executed and variable changes in real time.

    Local AI – explain, fix, generate code using a GGUF model (requires llama-cpp-python).

    Integrated shell – run any system command directly from the menu.

    File management – Open, Save, Save As, Rename.

    Auto‑heal – when enabled, AI automatically fixes errors and re‑runs your code.

    Fully offline – no external API calls.

📦 Requirements

    Python 3.8 or newer.

    A terminal with at least 20 rows × 50 columns (recommended; smaller works with a warning).

    Optional: a GGUF model file (e.g., codellama-7b.Q4_K_M.gguf) for AI features.

🔧 Installation

    Install Python dependencies:
    bash

    pip install llama-cpp-python

    (If you don't need AI, you can skip this; AI commands will show an error.)

    Download the script – save the provided anioxaz_cli.py file to your computer.

    (Optional) Download a GGUF model – get one from Hugging Face (e.g., TheBloke/CodeLlama-7B-GGUF).

🚀 How to Use
Launch the application
bash

python3 anioxaz_cli.py

Main Menu

    ↑ / ↓ – move selection.

    Enter – select the highlighted action.

    ESC – from any sub‑mode (editor, shell, prompt) returns to the main menu.

Menu Items
Item	What it does
Editor	Enters the code editor. Type code, navigate with arrows, Home/End, Page Up/Down, Tab for indentation. Press ESC to return to the menu.
Run	Executes the current code. Output appears in the middle pane. Live tracing shows each line and variable changes.
Explain	AI explains what your code does (requires loaded model).
Fix	AI tries to fix your code. You'll be prompted for an error description.
Generate	Generate Python code from a natural language description.
File	Opens a sub‑menu: Open, Save, Save As, Rename, Back.
Model	Load a GGUF model from a file path (prompt appears).
Shell	Enter shell mode – type any system command (e.g., ls, pip install requests). Press Enter to run, ESC to return.
AutoHeal	Toggles automatic healing on/off (when on, errors trigger AI fix + re‑run).
Help	Shows this help text in the output pane.
Exit	Quit the application.
Prompts

When you select Fix, Generate, Open, Save As, Rename, or Model, a yellow prompt appears at the bottom. Type your answer and press Enter. Press ESC to cancel.
🖥️ Screen Layout

    Top – red banner with "ANIOXAZ".

    Below – vertical menu (or editor when active).

    Middle – output pane (shows program output, trace events, AI responses, shell output).

    Bottom – blue status bar (shows file name, model, auto‑heal status, current state).

    Bottom line – prompt or shell input (temporary).

🧪 Example Workflow

    Start the app.

    Select Editor and write a Python script (e.g., print("Hello")).

    Press ESC to return to the menu.

    Select Run – see the output and trace in the middle pane.

    Select Model and enter the path to your GGUF model.

    Select Explain – AI describes your code.

    Select Shell, type pip install requests, and see the installation output.

    Press ESC to go back to the menu.

⚠️ Troubleshooting
"Terminal too small" error

The app works best with at least 20 rows and 50 columns.
If your terminal is smaller, you'll see a message. Resize your terminal, or remove the size check in the code (search for if self.rows < 20 or self.cols < 50 and comment it out).
Colors not showing / curses errors

    Some terminals don't support colors. You can disable colors by commenting out the _init_colors() call inside run().

    If you see curses.error: addstr() returned ERR, your terminal is too small – enlarge it or use the workaround above.

AI commands return "No model loaded"

Load a model first via the Model menu item.
👤 Author

Rehan Aman
Built with ❤️ for offline coding.
📄 License

MIT – feel free to use, modify, and share.
