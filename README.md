
# GUI 4 HEMTT

Cross-platform PySide6 GUI for the [HEMTT](https://hemtt.dev) CLI tool (Windows & Linux).

## Features

- Main workflow commands with dialogs:
  - `hemtt check` (`-p`, `-e`, `-L`, threads, verbosity)
  - `hemtt dev` (`-b`, `--no-rap`, optionals, `--just`, threads, verbosity)
  - `hemtt launch` (profiles/config chain, `-e`, `-i`, `-Q`, `-F`, optionals, `-b`, `--no-rap`, passthrough args, threads, verbosity)
  - `hemtt build` (`--no-bin`, `--no-rap`, `--just`, threads, verbosity)
  - `hemtt release` (`--no-bin`, `--no-rap`, `--no-sign`, `--no-archive`, threads, verbosity)
- Localization and cleanup helpers:
  - `hemtt localization sort` (`--only-lang`)
  - `hemtt localization coverage` (`--format`)
  - `hemtt utils fnl`
  - `hemtt utils bom`
- Utility command coverage:
  - `hemtt utils inspect`
  - `hemtt utils verify`
  - `hemtt utils paa convert`
  - `hemtt utils paa inspect` (`--format`)
  - `hemtt utils pbo inspect` (`--format`)
  - `hemtt utils pbo unpack` (optional output path, optional `-r/--derap`)
  - `hemtt utils pbo extract`
  - `hemtt utils audio inspect|convert|compress` (convert supports `-c` for WSS output)
  - `hemtt utils config inspect|derapify` (`-f` format)
  - `hemtt utils p3d json`
  - `hemtt utils sqf case`
  - `hemtt wiki force-pull`
- Project commands:
  - `hemtt new`
  - `hemtt license`
  - `hemtt script`
  - `hemtt value`
  - `hemtt keys generate` (including optional advanced KDF settings)
- UI and quality-of-life:
  - Live command output with basic severity highlighting
  - Dark/light mode toggle
  - Drag-and-drop project folder support
  - Persistent config (`hemtt` path, project directory, Arma 3 executable, theme)
  - Custom argument runner for any unsupported/advanced command
  - Windows-only: Install/update HEMTT via winget

## Requirements

- Python 3.11+
- PySide6 (see requirements.txt)
- HEMTT CLI (install separately)

## Quick Start

```sh
pip install -r requirements.txt
python hemtt_gui.py
```

## Running Tests

```sh
python -m unittest tools.tests -v
```

The test suite validates command construction, configuration persistence, and argument-building behavior.

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

Use the tasks in `.vscode/tasks.json` for build/run/test workflows:

- `Run Application (Python, Windows)`
- `Run Tests`
- `Build Executable (Windows)`
- `Clean and Build (Windows)`

## Notes

- HEMTT must be in your PATH or set in the GUI.
- Some features (like winget) are Windows-only.
- On Linux, a terminal emulator (gnome-terminal, konsole, xterm) is required for some features.
- The GUI aims to cover commonly used HEMTT commands; unsupported flags/commands can always be run via `Custom args`.

## License

MIT — see LICENSE
