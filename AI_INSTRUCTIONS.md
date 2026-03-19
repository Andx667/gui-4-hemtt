# AI Instructions for GUI 4 HEMTT

## Project Overview

**GUI 4 HEMTT** is a cross-platform desktop application that provides a graphical user interface for the [HEMTT](https://hemtt.dev) command-line tool. HEMTT is a build system for Arma 3 mod development. This GUI simplifies interaction with HEMTT by providing one-click access to all major commands with live process output and persistent configuration.

### Target Audience
- Arma 3 mod developers who use HEMTT for building and managing their projects
- Users who prefer GUI over CLI for HEMTT operations
- Both Windows and Linux users

### Key Use Cases
- Building Arma 3 mods with various configurations (dev, release, check, launch)
- Managing HEMTT project settings visually
- Monitoring build processes with live output
- Installing/updating HEMTT (Windows via winget)

## Technology Stack

- **Language**: Python 3.11+ (with type hints)
- **GUI Framework**: PySide6 (Qt for Python) >= 6.5.0
- **Build Tool**: PyInstaller (for creating standalone executables)
- **Linting/Formatting**: Ruff, Black (configured in pyproject.toml)
- **Type Checking**: MyPy (configured in pyproject.toml)
- **External Dependency**: HEMTT CLI tool (not bundled, must be in PATH)

## Project Structure

```
gui-4-hemtt/
├── hemtt_gui.py           # Main application entry point & GUI classes
├── command_runner.py      # Background process execution utilities
├── config_store.py        # Configuration persistence (JSON)
├── config.json            # User configuration file (generated at runtime)
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata & tool configurations
├── GUI-4-hemtt.spec       # PyInstaller build specification
├── README.md              # User documentation
├── CHANGES.md             # Detailed changelog and implementation notes
├── LICENSE                # MIT License
│
├── .vscode/
│   └── tasks.json         # VS Code build/run tasks (Windows & Linux)
│
├── assets/
│   ├── icon.ico           # Windows application icon
│   ├── logo.png           # Linux application icon
│   └── screenshot.png     # Documentation screenshot
│
├── tools/
│   ├── tests.py           # Unit tests
│   └── convert_icon.py    # Icon conversion utility
│
├── build/                 # PyInstaller build artifacts (gitignored)
├── dist/                  # PyInstaller output executables (gitignored)
└── __pycache__/           # Python bytecode cache (gitignored)
```

## Architecture & Design Patterns

### Modular Design

1. **hemtt_gui.py** - Contains all GUI classes:
   - `HemttGUI` (QMainWindow) - Main application window
   - `BaseCommandDialog` - Reusable dialog base class with common controls
    - Command-specific dialogs: `BuildDialog`, `DevDialog`, `CheckDialog`, `ReleaseDialog`, `LaunchDialog`, `LocalizationCoverageDialog`, `LocalizationSortDialog`
    - File-based utility handlers for PAA/PBO/audio/config/P3D/SQF commands
    - Project and maintenance command handlers (`new`, `license`, `script`, `value`, `keys`, `wiki`)

2. **command_runner.py** - Process execution:
   - `CommandRunner` class - Threaded subprocess wrapper with callbacks
   - `build_command()` - Command construction helper
   - `strip_ansi_codes()` - Terminal color code removal

3. **config_store.py** - Persistence layer:
   - `load_config()` - Load JSON config with defaults fallback
   - `save_config()` - Persist config to disk
   - `DEFAULTS` - Default configuration values

### Key Concepts

- **Thread Safety**: Commands run in background threads (`CommandRunner`) and communicate via `queue.Queue` to avoid blocking the UI
- **Timer-based Polling**: QTimer polls the output queue every 100ms to update the UI
- **Config Persistence**: All user preferences (paths, dark mode, verbosity) are saved to `config.json`
- **Drag & Drop**: Main window accepts folder drops to set project directory
- **Cross-platform**: Uses `sys.platform` checks for OS-specific behavior (winget, terminal emulators)
- **Dark Mode**: Custom QPalette-based theming with automatic UI updates

## Coding Guidelines

### Style & Formatting

Follow the settings in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "B", "UP"]
ignore = ["E501"]

[tool.black]
line-length = 100
target-version = ["py311"]
```

**Key Rules:**
- Maximum line length: 100 characters
- Use double quotes for strings
- Use spaces for indentation (4 spaces)
- Import sorting follows isort conventions
- Type hints required (checked by MyPy)

### Type Hints

All functions should include type annotations:
```python
def function_name(param: str, optional: int | None = None) -> bool:
    """Docstring here."""
    ...
```

Use modern union syntax: `str | None` instead of `Optional[str]`

### Docstrings

Use NumPy-style docstrings with sections:
```python
def example_function(arg1: str, arg2: int) -> str:
    """Brief one-line description.

    Parameters
    ----------
    arg1: str
        Description of arg1.
    arg2: int
        Description of arg2.

    Returns
    -------
    str
        Description of return value.
    """
```

### Error Handling

- Catch specific exceptions, not bare `except:`
- Use `try/except` blocks around file I/O, subprocess calls, and JSON operations
- Fail gracefully with user-friendly error messages (QMessageBox)
- Log errors to console but don't crash the application

### Qt/PySide6 Patterns

- Always call `super().__init__()` in widget constructors
- Use type hints for Qt types: `QWidget`, `QDialog`, etc.
- Connect signals properly: `button.clicked.connect(self.method_name)`
- Update UI from main thread only (use queue for background thread → UI communication)
- Call `setObjectName()` for widgets that need styling

## Command-Line Interface Patterns

### Building HEMTT Commands

Use `build_command()` from `command_runner.py`:
```python
from command_runner import build_command

hemtt_path = "hemtt"
args = ["build", "--release", "-v"]
cmd = build_command(hemtt_path, args)  # ["hemtt", "build", "--release", "-v"]
```

### Running Commands

Use the `CommandRunner` class:
```python
runner = CommandRunner(
    command=cmd,
    cwd=project_directory,
    on_output=self._handle_line,
    on_exit=self._on_exit
)
runner.start()
```

## Configuration Management

### Default Configuration

See `config_store.py` for the `DEFAULTS` dictionary:
- `hemtt_path`: Path to HEMTT executable (default: "hemtt")
- `project_dir`: Working directory (default: current directory)
- `dark_mode`: UI theme preference (default: False)
- `verbose`: Global verbosity toggle (default: False)
- `pedantic`: Pedantic checking (default: False)

### Saving/Loading

```python
from config_store import load_config, save_config

config = load_config()
config["dark_mode"] = True
save_config(config)
```

## Build & Deployment

### Development

Run directly with Python:
```bash
python hemtt_gui.py
```

Or use VS Code task: "Run Application (Python, Windows)"

### Building Executables

**Windows:**
```bash
pyinstaller --clean --name GUI-4-hemtt --windowed --onefile --icon=assets/icon.ico hemtt_gui.py
```

**Linux:**
```bash
pyinstaller --clean --name GUI-4-hemtt --windowed --onefile --icon=assets/logo.png hemtt_gui.py
```

Output: `dist/GUI-4-hemtt.exe` (Windows) or `dist/GUI-4-hemtt` (Linux)

### VS Code Tasks

Use the predefined tasks in `.vscode/tasks.json`:
- **Build Executable (Windows)** - Clean build for Windows
- **Build Executable (Linux)** - Clean build for Linux
- **Clean Build Artifacts** - Remove build/dist directories
- **Run Application (Python)** - Run from source
- **Run Tests** - Execute unit tests

## Testing

Unit tests are in `tools/tests.py`. Run with:
```bash
python -m unittest tools.tests -v
```

Or use VS Code task: "Run Tests"

## Platform-Specific Considerations

### Windows-Only Features

- **winget integration**: Install/update HEMTT via Windows Package Manager
- **Interactive terminal launch for select commands**: Uses `powershell.exe -NoExit`
- Uses `cmd.exe` as shell in VS Code tasks

### Linux-Only Features

- **Terminal emulator detection**: Checks for gnome-terminal, konsole, xterm
- Uses `/bin/bash` as shell in VS Code tasks

### Cross-Platform Code

Use platform checks:
```python
import sys

if sys.platform == "win32":
    # Windows-specific code
    pass
elif sys.platform.startswith("linux"):
    # Linux-specific code
    pass
```

## Important Notes for AI Assistants

1. **Never break existing functionality**: The application is fully functional. Changes should be additive or improvements only.

2. **Test cross-platform**: Any changes affecting file paths, subprocesses, or UI must work on both Windows and Linux.

3. **Preserve config compatibility**: Changes to `config_store.py` must maintain backward compatibility with existing `config.json` files.

4. **Respect HEMTT CLI**: This is a wrapper, not a replacement. All commands should map directly to HEMTT's actual CLI interface.

5. **Type safety**: Always add type hints. The project uses MyPy for static type checking.

6. **UI threading**: Never block the main UI thread. Long-running operations must use `CommandRunner` or separate threads.

7. **Error messages**: Use `QMessageBox` for user-facing errors, not console prints or exceptions.

8. **Dark mode**: When adding UI elements, ensure they respect the `self.current_theme` dictionary for color styling.

9. **Config persistence**: Any new user preferences should be added to `config_store.DEFAULTS` and properly saved/loaded.

10. **Documentation**: Update `README.md` for user-facing changes and `CHANGES.md` for implementation details.

## Common Tasks & Examples

### Adding a New Command Dialog

1. Subclass `BaseCommandDialog` in `hemtt_gui.py`
2. Override `_build_dialog_options()` to add command-specific controls
3. Override `build_args()` to construct the argument list
4. Add a button in `HemttGUI._build_ui()` that opens the dialog
5. Connect the dialog's accepted signal to `_run_hemtt_dialog()`

### Adding a New Config Option

1. Add default value to `DEFAULTS` in `config_store.py`
2. Add UI control in `HemttGUI._build_ui()`
3. Load value in `_load_config_into_ui()`
4. Save value in `_persist_config()`

### Modifying Command Output Display

Edit `_handle_line()` in `HemttGUI` - this method receives each line from the subprocess.

### Changing Theme Colors

Edit `_setup_themes()` in `HemttGUI` - modifies the `self.light_theme` and `self.dark_theme` dictionaries.

## External Resources

- [HEMTT Documentation](https://hemtt.dev) - Official HEMTT docs
- [PySide6 Documentation](https://doc.qt.io/qtforpython-6/) - Qt for Python reference
- [PyInstaller Manual](https://pyinstaller.org/en/stable/) - Executable building guide

## License

This project is MIT licensed. See LICENSE file for full text.
