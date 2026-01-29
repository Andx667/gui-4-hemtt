# GUI 4 HEMTT

A lightweight cross-platform (Windows-focused) PySide6 (Qt6) GUI wrapper for the [`hemtt`](https://hemtt.dev) CLI tool.

## Screenshot

Below is an example of the GUI in use (dark mode with build options visible).

![HEMTT GUI Screenshot](assets/screenshot.png)

## Features

- **One-click core commands**: `hemtt build`, `hemtt dev`, `hemtt check`, `hemtt release`, `hemtt launch` - all with comprehensive option dialogs.
- **Command-specific dialogs**: Each main command (check, dev, build, release, launch) opens a dedicated dialog with command-specific options and global settings.
- **Winget convenience**: `Install HEMTT (winget)` and `Update HEMTT (winget)` buttons (Windows) to install or upgrade the `BrettMayson.HEMTT` package.
- **Helper commands**: `hemtt localization sort`, `hemtt localization coverage`, `hemtt utils fnl`, `hemtt utils bom`, `hemtt utils pbo inspect`, `hemtt utils pbo unpack`, `hemtt utils paa convert`, `hemtt utils paa inspect`, `hemtt book`.
- **Project commands**: `hemtt new <project>`, `hemtt license [name]`, `hemtt script <name>`, `hemtt value <key>`, `hemtt keys generate`.
- **Command options**:
  - **Check**: Pedantic mode (`-p`), treat warnings as errors (`-e`), custom lints (`-L`), verbosity levels (None/-v/-vv), threads (`-t`)
  - **Dev**: Binarize (`-b`), no-rap (`--no-rap`), all-optionals (`-O`), specific optionals (`-o`), just addon (`--just`), verbosity, threads
  - **Build**: No-bin (`--no-bin`), no-rap (`--no-rap`), just addon (`--just`), verbosity, threads
  - **Release**: No-bin (`--no-bin`), no-rap (`--no-rap`), no-sign (`--no-sign`), no-archive (`--no-archive`), verbosity, threads
  - **Launch**: Profiles/configs, quick mode (`-Q`), no filepatching (`-F`), binarize (`-b`), no-rap, optionals (`-o`/`-O`), executable override (`-e`), instances (`-i`), just addon, passthrough args, verbosity, threads
  - **Localization Coverage**: Output format selection (ascii, json, pretty-json, markdown)
  - **Localization Sort**: Only sort languages option (`--only-lang`)
- **Profile support for launch**: Specify launch profiles, CDLC shortcuts (e.g., `+ws`), and global profiles (e.g., `@adt`).
- **Verbosity control**: Three-level verbosity (Normal, Debug `-v`, Trace `-vv`) via radio buttons in command dialogs.
- **Tooltips**: All buttons feature informative hover tooltips explaining each command.
- **Dark / Light mode toggle**: Fully styled controls with consistent theming across main window and dialogs.
- **Open HEMTT Log**: Quick access to `.hemttout/latest.log` in your default text editor.
- **Organized UI**: Labeled sections (Main Commands, Helper Commands, Project Commands, Utilities) with visual dividers.
- **Drag & Drop**: Drop a folder anywhere in the main window to set the project directory.
- **Persistent configuration**: HEMTT executable, project directory, Arma 3 executable, and dark mode preference stored in `config.json`.
- **Color-coded console output**: Basic severity detection (error / warning / info) with appropriate highlighting.
- **Live status updates**: Elapsed time and status bar with real-time updates during command execution.
- **Process cancellation**: Cancel running commands at any time.
- **Custom arguments**: Enter additional arguments exactly as you would after `hemtt` on the CLI.

## Requirements

- Python 3.11+ (3.12 recommended).
- `hemtt` installed and available in PATH, or set via browse.
- PySide6 6.5.0+ (Qt6 framework).

## Installation

Install dependencies:

```pwsh
pip install -r requirements.txt
```

Or manually:

```pwsh
pip install PySide6>=6.5.0
```

## Running

```pwsh
python hemtt_gui.py
```

Use the Browse buttons to set your project directory and (optionally) the `hemtt` executable path.

### Installing / Updating HEMTT (Windows)

If you don't have HEMTT yet (or want to upgrade), use the top two buttons:

- `Install HEMTT (winget)` → runs: `winget install --id BrettMayson.HEMTT -e`
- `Update HEMTT (winget)` → runs: `winget upgrade --id BrettMayson.HEMTT -e`

You can do the same manually in a terminal:

```pwsh
winget search hemtt
winget install --id BrettMayson.HEMTT -e
winget upgrade --id BrettMayson.HEMTT -e
```

After installation, ensure `hemtt` resolves in PATH or browse directly to its executable.

## Using Command Dialogs

All main commands (check, dev, build, release, launch) open a dialog where you can configure options:

### Check Dialog
- **Pedantic mode**: Enable all optional lints
- **Treat warnings as errors**: Make warnings fail the check
- **Custom lints**: Specify individual lints to enable
- **Verbosity**: Choose Normal, Debug (-v), or Trace (-vv)
- **Threads**: Set number of threads to use

### Dev Dialog
- **Binarize**: Use BI's binarize on supported files
- **No rapify**: Skip rapification of config files
- **Optionals**: Include all or specific optional addons
- **Just addons**: Build only specific addons
- **Verbosity & Threads**: Standard options

### Build Dialog
- **No binarize**: Skip binarization
- **No rapify**: Skip rapification
- **Just addons**: Build only specific addons
- **Verbosity & Threads**: Standard options

### Release Dialog
- **No binarize**: Skip binarization
- **No rapify**: Skip rapification
- **No sign**: Don't sign PBOs or create bikey
- **No archive**: Don't create release zip
- **Verbosity & Threads**: Standard options

### Launch Dialog
- **Profiles**: Specify launch profiles (e.g., `default ace +ws`)
- **Quick launch**: Skip build, use last build
- **No file patching**: Disable file patching
- **Binarize/No rapify**: Dev build options
- **Optionals**: Include optional addons
- **Executable**: Override Arma 3 executable
- **Instances**: Launch multiple instances
- **Passthrough args**: Pass additional args to Arma 3 (after `--`)
- **Just addons**: Build only specific addons
- **Verbosity & Threads**: Standard options

### Localization Commands
- **Coverage**: Choose output format (ascii, json, pretty-json, markdown)
- **Sort**: Option to sort only languages within keys

## Project Commands

### hemtt new
Creates a new HEMTT project interactively. Enter a project name and a terminal window will open where HEMTT will guide you through the setup process (asking for mod name, author, prefix, etc.). The terminal will remain open after completion so you can review the output.

**Note:** This command opens in a separate terminal window because it requires interactive input.

### hemtt license
Add or update your project license. Choose from:
- `apl-sa` - Arma Public License Share Alike
- `apl` - Arma Public License
- `apl-nd` - Arma Public License No Derivatives
- `apache` - Apache 2.0
- `gpl` - GNU GPL v3
- `mit` - MIT
- `unlicense` - Unlicense
- `interactive` - Select interactively from HEMTT (opens in terminal)

When you select a specific license from the dropdown, it will be added directly. Choosing "interactive" opens a terminal window for the full HEMTT interactive license selection.

### hemtt script
Run a Rhai script from `.hemtt/scripts/`. Enter the script name without the `.rhai` extension.

### hemtt value
Print a value from your project configuration. Useful for CI/CD. Examples:
- `project.name`
- `project.version`
- `project.mainprefix`

### hemtt keys generate
Generate a new HEMTT private key for signing PBOs. Follow the interactive prompts.

## Custom Commands

Enter additional arguments exactly as you would after `hemtt` on the CLI. Example:

```text
validate
```

Then press Run.

You can also use multiple flags, e.g.

```text
dev --just core --just weapons -v -v
```

## Packaging (Windows executable)

### Using VS Code Tasks (Recommended)

Press `Ctrl+Shift+B` or run "Build Executable" from the Command Palette → Tasks menu.

### Manual Build

Using PyInstaller to create an optimized single-file executable:

```pwsh
pip install pyinstaller
pyinstaller --name HemttGUI --windowed --onefile --hidden-import=PySide6.QtCore --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets --exclude-module=PySide6.QtNetwork --exclude-module=PySide6.QtWebEngineWidgets --exclude-module=PySide6.QtWebEngineCore --exclude-module=PySide6.QtQml --exclude-module=PySide6.QtQuick --exclude-module=PySide6.QtMultimedia --exclude-module=PySide6.Qt3D --exclude-module=PySide6.QtCharts --exclude-module=PySide6.QtDataVisualization --exclude-module=PySide6.QtSql --exclude-module=matplotlib --exclude-module=numpy --exclude-module=pandas --strip hemtt_gui.py
```

This will produce `dist/HemttGUI.exe` (~40-50MB with optimizations).

Note: The executable is larger than tkinter versions (~8MB) because it includes the full Qt6 framework with modern UI capabilities.

## Code Structure

- `hemtt_gui.py` – Main PySide6 (Qt6) application.
- `command_runner.py` – Background process runner & output streaming.
- `config_store.py` – Simple JSON config persistence.
- `tests.py` – Basic helper tests.
- `requirements.txt` – Python dependencies.
- `.vscode/tasks.json` – VS Code build tasks.

## GitHub Actions: Build on Release

This repository includes a workflow at `.github/workflows/release.yml` that:

- Builds the Windows executable with PyInstaller (with size optimizations)
- Uses UPX compression to reduce executable size
- Attaches the `GUI-4-hemtt.exe` artifact to the GitHub Release

Trigger it by publishing a new Release in GitHub (or run manually via the Actions tab). Ensure Actions are enabled and the default `GITHUB_TOKEN` has `contents: write` (the workflow sets this).

## Limitations / Future Improvements

- No progress bar (HEMTT doesn't emit structured progress; could parse lines heuristically).
- Potential future: favorites list, output filtering (errors only), command history dropdown.
- Could add auto-switch to new project directory after `hemtt new` completes.
- Additional utils commands could be added (audio tools, config tools, etc.).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `hemtt` not found | Ensure it's installed or browse to executable. |
| Missing PySide6 module | Run `pip install -r requirements.txt` to install dependencies. |
| GUI freezes | Shouldn't happen; output runs in thread. Report issue. |
| No output until end | Some commands may buffer; run with extra verbosity (select `-v` or `-vv` in command dialog). |
| Buttons hard to see in dark mode | Fixed - dialogs now support dark mode styling. |
| Can't find HEMTT log file | Run a HEMTT command first to generate `.hemttout/latest.log`. |
| Dialog doesn't appear | Check that you're running the latest version with restored dialog functionality. |
| Options not taking effect | Ensure you click OK in the dialog; Cancel will abort the command. |
| Passthrough args not working | Make sure to use proper syntax (space-separated, e.g., `-world=empty -window`). |
| "not a terminal" error | This is now fixed - interactive commands (hemtt new, license interactive) open in a separate terminal window. |
| Terminal window doesn't open | Ensure PowerShell is available (Windows), or a terminal emulator is installed (Linux/macOS). |

## License

[MIT LICENSE](LICENSE)
