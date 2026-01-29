
# GUI 4 HEMTT

Cross-platform PySide6 GUI for the [HEMTT](https://hemtt.dev) CLI tool (Windows & Linux).

## Features

- One-click access to all major HEMTT commands (build, dev, check, release, launch)
- Command-specific dialogs with options
- Live process output, dark/light mode, persistent config
- Windows-only: Install/Update HEMTT via winget

## Requirements

- Python 3.11+
- PySide6 (see requirements.txt)
- HEMTT CLI (install separately)

## Quick Start

```sh
pip install -r requirements.txt
python hemtt_gui.py
```

## Build as Executable

**Windows:**

```sh
pip install pyinstaller
pyinstaller --clean --name GUI-4-hemtt --windowed --onefile --icon=assets/icon.ico hemtt_gui.py
```

**Linux:**

```sh
pip install pyinstaller
pyinstaller --clean --name GUI-4-hemtt --windowed --onefile --icon=assets/logo.png hemtt_gui.py
```

Result: `dist/GUI-4-hemtt(.exe)`

## VS Code Tasks

Use `.vscode/tasks.json` or `.vscode/tasks.crossplat.yaml` for cross-platform build/run.

## Notes

- HEMTT must be in your PATH or set in the GUI.
- Some features (like winget) are Windows-only.
- On Linux, a terminal emulator (gnome-terminal, konsole, xterm) is required for some features.

## License

MIT — see LICENSE
