anioxaz_cli.py – Usage Guide

Author: Rehan Aman
🚀 Launch

python anioxaz_cli.py

A split‑screen terminal UI appears:

    Top – code editor

    Middle – output console (program output, trace, AI responses, shell output)

    Bottom line – status bar (shows file, model status, auto‑heal toggle)

    Bottom input line – command prompt

⌨️ Editor Controls

    Arrows / Home / End / Page Up / Page Down – navigate

    Tab – insert 4 spaces

    Enter – new line

    Backspace / Delete – delete

    Type – insert text

🛠️ Command Mode (press :)

Press : to enter command mode (the prompt changes to :). Type a command and press Enter.
File Commands
Command	Action
:open filename.py	Open a Python file
:save	Save the current file
Code Execution
Command	Action
:run	Run the code with live tracing – shows each executed line and variable changes in the output pane
AI Commands (requires a model loaded)
Command	Action
:model /path/to/model.gguf	Load your local GGUF model (do once per session)
:explain	AI explains the current code
:fix	AI attempts to fix the code (you'll be asked for the error description)
:generate description	Generate Python code from natural language
:autoheal on/off	Toggle auto‑healing – on error, AI fixes and re‑runs automatically
Shell Commands

Any command not starting with : is executed in your system shell.
Examples: ls, pip install requests, python --version, echo "Hello"
Help
Command	Action
:help	Show a quick help summary in the output pane
📊 Tracing Output Example

After :run, you’ll see in the output pane:
text

=== Execution started ===
Trace: Line 1 executed
Trace: Var x=5
Trace: Line 2 executed
Trace: Var y=10
...
=== Execution finished ===

This gives you a real‑time view of your program’s inner workings.
🔁 Auto‑Heal Workflow

    Enable: :autoheal on

    Write code and :run

    If it crashes, the AI fixes the code, replaces it, and re‑runs automatically – all without interruption.

💡 Tips

    Always load a model first (:model) before using AI commands.

    Use :run frequently to test and trace.

    Press Esc to cancel command mode and return to editing.

Happy coding with your offline AI partner!
— Rehan Aman
