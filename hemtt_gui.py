import os
import queue
import shutil
import sys
import time
import webbrowser

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from command_runner import CommandRunner, build_command
from config_store import load_config, save_config

APP_TITLE = "GUI 4 HEMTT"


class HemttGUI(QMainWindow):
    """PySide6-based GUI wrapper around the HEMTT CLI.

    Provides buttons for common commands, live process output, and user
    preferences such as dark mode and verbosity toggles.
    """

    def __init__(self):
        """Initialize the main application window and state."""
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(800, 500)
        self.setAcceptDrops(True)

        # State
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.runner: CommandRunner | None = None
        self.running: bool = False
        self.start_time: float = 0.0
        self.dark_mode: bool = False
        self.current_theme: dict = {}  # Will be set by theme setup

        # Load config
        self.config_data = load_config()

        # Build UI
        self._build_ui()
        self._load_config_into_ui()

        # Setup timer for polling output queue
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_output_queue)
        self.poll_timer.start(100)  # Poll every 100ms

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag events with file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle folder drops on main window to set project directory."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                # Check if it's a directory
                if os.path.isdir(path):
                    self.proj_entry.setText(path)
                    self._persist_config()
                else:
                    # If file was dropped, use its parent directory
                    parent_dir = os.path.dirname(path)
                    if os.path.isdir(parent_dir):
                        self.proj_entry.setText(parent_dir)
                        self._persist_config()

    def _build_ui(self) -> None:
        """Create and lay out all UI widgets."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Set button styling for better visibility
        self.light_button_style = """
            QPushButton {
                border: 1px solid #888;
                border-radius: 4px;
                padding: 5px 15px;
                background-color: #f0f0f0;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border: 1px solid #666;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999;
                border: 1px solid #ccc;
            }
        """

        self.dark_button_style = """
            QPushButton {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px 15px;
                background-color: #3a3a3a;
                color: #e0e0e0;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #666;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #2f2f2f;
                color: #666;
                border: 1px solid #444;
            }
        """

        # Start with light mode style
        self.button_style = self.light_button_style

        # Winget install/update frame (top-most)
        winget_layout = QHBoxLayout()
        self.btn_install_hemtt = QPushButton("Install HEMTT (winget)")
        self.btn_install_hemtt.setStyleSheet(self.button_style)
        self.btn_install_hemtt.setToolTip(
            "Install HEMTT via Windows Package Manager\nRequires winget to be installed"
        )
        self.btn_install_hemtt.clicked.connect(self._install_hemtt)

        self.btn_update_hemtt = QPushButton("Update HEMTT (winget)")
        self.btn_update_hemtt.setStyleSheet(self.button_style)
        self.btn_update_hemtt.setToolTip(
            "Update HEMTT to latest version\nUses Windows Package Manager"
        )
        self.btn_update_hemtt.clicked.connect(self._update_hemtt)

        winget_layout.addWidget(self.btn_install_hemtt)
        winget_layout.addWidget(self.btn_update_hemtt)
        winget_layout.addStretch()
        main_layout.addLayout(winget_layout)

        # Top frame for paths
        paths_grid = QGridLayout()

        # HEMTT executable path
        hemtt_label = QLabel("HEMTT executable:")
        self.hemtt_entry = QLineEdit()
        self.hemtt_browse = QPushButton("Browse…")
        self.hemtt_browse.setStyleSheet(self.button_style)
        self.hemtt_browse.clicked.connect(self._browse_hemtt)
        paths_grid.addWidget(hemtt_label, 0, 0)
        paths_grid.addWidget(self.hemtt_entry, 0, 1)
        paths_grid.addWidget(self.hemtt_browse, 0, 2)

        # Project directory
        proj_label = QLabel("Project directory:")
        self.proj_entry = QLineEdit()
        self.proj_browse = QPushButton("Browse…")
        self.proj_browse.setStyleSheet(self.button_style)
        self.proj_browse.clicked.connect(self._browse_project)
        paths_grid.addWidget(proj_label, 1, 0)
        paths_grid.addWidget(self.proj_entry, 1, 1)
        paths_grid.addWidget(self.proj_browse, 1, 2)

        # Arma 3 executable path
        arma3_label = QLabel("Arma 3 executable:")
        self.arma3_entry = QLineEdit()
        self.arma3_browse = QPushButton("Browse…")
        self.arma3_browse.setStyleSheet(self.button_style)
        self.arma3_browse.clicked.connect(self._browse_arma3)
        paths_grid.addWidget(arma3_label, 2, 0)
        paths_grid.addWidget(self.arma3_entry, 2, 1)
        paths_grid.addWidget(self.arma3_browse, 2, 2)

        paths_grid.setColumnStretch(1, 1)
        main_layout.addLayout(paths_grid)

        # Separator with title for main commands
        main_commands_label = QLabel("Main Commands")
        font = main_commands_label.font()
        font.setBold(True)
        main_commands_label.setFont(font)
        main_layout.addWidget(main_commands_label)

        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator1)

        # Buttons frame - First row
        btns_layout = QHBoxLayout()

        self.btn_check = QPushButton("hemtt check")
        self.btn_check.setStyleSheet(self.button_style)
        self.btn_check.setToolTip(
            "Check project for errors\nQuick validation without building files"
        )
        self.btn_check.clicked.connect(self._run_check)

        self.btn_dev = QPushButton("hemtt dev")
        self.btn_dev.setStyleSheet(self.button_style)
        self.btn_dev.setToolTip("Build for development\nCreates symlinks for file-patching")
        self.btn_dev.clicked.connect(self._run_dev)

        self.btn_launch = QPushButton("hemtt launch")
        self.btn_launch.setStyleSheet(self.button_style)
        self.btn_launch.setToolTip(
            "Build and launch Arma 3\nAutomatically loads mods and dependencies"
        )
        self.btn_launch.clicked.connect(self._run_launch)

        self.btn_build = QPushButton("hemtt build")
        self.btn_build.setStyleSheet(self.button_style)
        self.btn_build.setToolTip("Build for local testing\nBinarizes files for final testing")
        self.btn_build.clicked.connect(self._run_build)

        self.btn_release = QPushButton("hemtt release")
        self.btn_release.setStyleSheet(self.button_style)
        self.btn_release.setToolTip("Build for release\nCreates signed PBOs and archives")
        self.btn_release.clicked.connect(self._run_release)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet(self.button_style)
        self.btn_cancel.clicked.connect(self._cancel_run)
        self.btn_cancel.setEnabled(False)

        btns_layout.addWidget(self.btn_check)
        btns_layout.addWidget(self.btn_dev)
        btns_layout.addWidget(self.btn_launch)
        btns_layout.addWidget(self.btn_build)
        btns_layout.addWidget(self.btn_release)

        # Vertical separator
        v_separator = QFrame()
        v_separator.setFrameShape(QFrame.VLine)
        v_separator.setFrameShadow(QFrame.Sunken)
        btns_layout.addWidget(v_separator)

        btns_layout.addWidget(self.btn_cancel)
        btns_layout.addStretch()
        main_layout.addLayout(btns_layout)

        # Separator with title for helper commands
        helper_commands_label = QLabel("Helper Commands")
        helper_commands_label.setFont(font)
        main_layout.addWidget(helper_commands_label)

        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator2)

        # Buttons frame - Second row
        btns2_layout = QHBoxLayout()

        self.btn_ln_sort = QPushButton("hemtt ln sort")
        self.btn_ln_sort.setStyleSheet(self.button_style)
        self.btn_ln_sort.setToolTip(
            "Sort stringtable entries\nOrganizes localization keys alphabetically"
        )
        self.btn_ln_sort.clicked.connect(self._run_ln_sort)

        self.btn_ln_coverage = QPushButton("hemtt ln coverage")
        self.btn_ln_coverage.setStyleSheet(self.button_style)
        self.btn_ln_coverage.setToolTip("Check stringtable coverage\nFinds missing translations")
        self.btn_ln_coverage.clicked.connect(self._run_ln_coverage)

        self.btn_utils_fnl = QPushButton("hemtt utils fnl")
        self.btn_utils_fnl.setStyleSheet(self.button_style)
        self.btn_utils_fnl.setToolTip(
            "Insert final newline into files if missing\nEnsures files end with newline (POSIX standard)"
        )
        self.btn_utils_fnl.clicked.connect(self._run_utils_fnl)

        self.btn_utils_bom = QPushButton("hemtt utils bom")
        self.btn_utils_bom.setStyleSheet(self.button_style)
        self.btn_utils_bom.setToolTip(
            "Remove UTF-8 BOM markers from files\nFixes parsing issues caused by Byte Order Marks"
        )
        self.btn_utils_bom.clicked.connect(self._run_utils_bom)

        self.btn_book = QPushButton("hemtt book")
        self.btn_book.setStyleSheet(self.button_style)
        self.btn_book.setToolTip("Open HEMTT documentation\nOpens hemtt.dev in your browser")
        self.btn_book.clicked.connect(self._open_book)

        btns2_layout.addWidget(self.btn_ln_sort)
        btns2_layout.addWidget(self.btn_ln_coverage)
        btns2_layout.addWidget(self.btn_utils_fnl)
        btns2_layout.addWidget(self.btn_utils_bom)
        btns2_layout.addWidget(self.btn_book)
        btns2_layout.addStretch()
        main_layout.addLayout(btns2_layout)

        # Third row for PAA/PBO utility buttons
        btns3_layout = QHBoxLayout()

        self.btn_paa_convert = QPushButton("hemtt paa convert")
        self.btn_paa_convert.setStyleSheet(self.button_style)
        self.btn_paa_convert.setToolTip(
            "Convert image to/from PAA format\nSupports PNG, JPEG, BMP, etc."
        )
        self.btn_paa_convert.clicked.connect(self._run_paa_convert)

        self.btn_paa_inspect = QPushButton("hemtt paa inspect")
        self.btn_paa_inspect.setStyleSheet(self.button_style)
        self.btn_paa_inspect.setToolTip(
            "Inspect a PAA file\nShows PAA properties in various formats"
        )
        self.btn_paa_inspect.clicked.connect(self._run_paa_inspect)

        self.btn_pbo_inspect = QPushButton("hemtt pbo inspect")
        self.btn_pbo_inspect.setStyleSheet(self.button_style)
        self.btn_pbo_inspect.setToolTip(
            "Inspect a PBO file\nShows PBO properties and contents in various formats"
        )
        self.btn_pbo_inspect.clicked.connect(self._run_pbo_inspect)

        self.btn_pbo_unpack = QPushButton("hemtt pbo unpack")
        self.btn_pbo_unpack.setStyleSheet(self.button_style)
        self.btn_pbo_unpack.setToolTip(
            "Unpack a PBO file\nExtracts PBO contents with optional derapification"
        )
        self.btn_pbo_unpack.clicked.connect(self._run_pbo_unpack)

        btns3_layout.addWidget(self.btn_paa_convert)
        btns3_layout.addWidget(self.btn_paa_inspect)
        btns3_layout.addWidget(self.btn_pbo_inspect)
        btns3_layout.addWidget(self.btn_pbo_unpack)
        btns3_layout.addStretch()
        main_layout.addLayout(btns3_layout)

        # Separator with title for utility buttons
        utilities_label = QLabel("Utilities")
        utilities_label.setFont(font)
        main_layout.addWidget(utilities_label)

        separator3 = QFrame()
        separator3.setFrameShape(QFrame.HLine)
        separator3.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator3)

        # Utility buttons frame
        util_btns_layout = QHBoxLayout()

        # Dark mode toggle
        self.btn_dark_mode = QPushButton("Toggle Dark Mode")
        self.btn_dark_mode.setStyleSheet(self.button_style)
        self.btn_dark_mode.clicked.connect(self._toggle_dark_mode)
        util_btns_layout.addWidget(self.btn_dark_mode)
        util_btns_layout.addStretch()
        main_layout.addLayout(util_btns_layout)

        # Custom command
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Custom args (after 'hemtt'):"))
        self.custom_entry = QLineEdit()
        custom_layout.addWidget(self.custom_entry, 1)
        self.btn_custom = QPushButton("Run")
        self.btn_custom.setStyleSheet(self.button_style)
        self.btn_custom.clicked.connect(self._run_custom)
        custom_layout.addWidget(self.btn_custom)
        main_layout.addLayout(custom_layout)

        # Output area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QApplication.font())  # Will be set to monospace later
        font_mono = self.output.font()
        font_mono.setFamily("Consolas")
        font_mono.setPointSize(10)
        self.output.setFont(font_mono)
        main_layout.addWidget(self.output, 1)  # Stretch factor 1 to expand

        # Store initial colors for theme switching
        self._setup_themes()

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.elapsed_label = QLabel("")
        status_layout.addWidget(self.elapsed_label)
        main_layout.addLayout(status_layout)

    def _setup_themes(self):
        """Setup light and dark mode color schemes and apply initial theme."""
        self.light_theme = {
            "bg": QColor("#f0f0f0"),
            "fg": QColor("black"),
            "base": QColor("white"),
            "text_bg": QColor("#f5f5f5"),
            "text_fg": QColor("#333333"),
            "error": QColor("#cc0000"),
            "warning": QColor("#ff8c00"),
            "info": QColor("#0066cc"),
        }
        self.dark_theme = {
            "bg": QColor("#2d2d2d"),
            "fg": QColor("#d4d4d4"),
            "base": QColor("#3c3c3c"),
            "text_bg": QColor("#0c0c0c"),
            "text_fg": QColor("#cccccc"),
            "error": QColor("#ff5555"),
            "warning": QColor("#ffff55"),
            "info": QColor("#55ffff"),
        }
        # Load dark mode preference from config
        self.dark_mode = self.config_data.get("dark_mode", False)
        if self.dark_mode:
            self._apply_dark_mode()
        else:
            self._apply_light_mode()

    def _load_config_into_ui(self) -> None:
        """Populate the UI from the persisted configuration file."""
        hemtt_path = self.config_data.get("hemtt_path") or "hemtt"
        proj_dir = self.config_data.get("project_dir") or os.getcwd()
        arma3_path = self.config_data.get("arma3_executable") or ""
        self.hemtt_entry.setText(hemtt_path)
        self.proj_entry.setText(proj_dir)
        self.arma3_entry.setText(arma3_path)

    def _browse_hemtt(self) -> None:
        """Open a file dialog to select the HEMTT executable and persist path."""
        initial = self.hemtt_entry.text() or os.getcwd()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select HEMTT executable",
            os.path.dirname(initial) if os.path.isfile(initial) else initial,
            "All files (*.*)",
        )
        if path:
            self.hemtt_entry.setText(path)
            self._persist_config()

    def _browse_project(self) -> None:
        """Open a folder dialog to select the project directory and persist it."""
        initial = self.proj_entry.text() or os.getcwd()
        path = QFileDialog.getExistingDirectory(self, "Select project directory", initial)
        if path:
            self.proj_entry.setText(path)
            self._persist_config()

    def _browse_arma3(self) -> None:
        """Open a file dialog to select the Arma 3 executable and persist path."""
        initial = self.arma3_entry.text()
        initialdir = (
            os.path.dirname(initial) if initial and os.path.isfile(initial) else os.getcwd()
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Arma 3 executable", initialdir, "Executable (*.exe);;All files (*.*)"
        )
        if path:
            self.arma3_entry.setText(path)
            self._persist_config()

    def _persist_config(self) -> None:
        """Write current UI settings and preferences to the config file."""
        save_config(
            {
                "hemtt_path": self.hemtt_entry.text().strip() or "hemtt",
                "project_dir": self.proj_entry.text().strip() or os.getcwd(),
                "arma3_executable": self.arma3_entry.text().strip(),
                "dark_mode": self.dark_mode,
            }
        )

    def _toggle_dark_mode(self) -> None:
        """Toggle between light and dark mode and persist preference."""
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self._apply_dark_mode()
        else:
            self._apply_light_mode()
        self._persist_config()

    def _apply_dark_mode(self) -> None:
        """Apply dark mode colors to the entire GUI."""
        self._apply_theme(self.dark_theme, self.dark_button_style)

    def _apply_light_mode(self) -> None:
        """Apply light mode colors to the entire GUI."""
        self._apply_theme(self.light_theme, self.light_button_style)

    def _apply_theme(self, theme: dict, button_style: str) -> None:
        """Apply a theme's colors and button styles to the GUI.

        Parameters
        ----------
        theme : dict
            Theme dictionary with color definitions
        button_style : str
            CSS stylesheet for buttons
        """
        palette = QPalette()
        palette.setColor(QPalette.Window, theme["bg"])
        palette.setColor(QPalette.WindowText, theme["fg"])
        palette.setColor(QPalette.Base, theme["base"])
        palette.setColor(QPalette.AlternateBase, theme["bg"])
        palette.setColor(QPalette.Text, theme["fg"])
        palette.setColor(QPalette.Button, theme["base"])
        palette.setColor(QPalette.ButtonText, theme["fg"])
        QApplication.setPalette(palette)

        # Store theme colors for text formatting
        self.current_theme = theme

        # Apply button styles
        self.button_style = button_style
        self._apply_button_styles()

    def _apply_button_styles(self) -> None:
        """Apply current button style to all buttons in the GUI."""
        # List of button attribute names
        button_attrs = [
            "btn_install_hemtt",
            "btn_update_hemtt",
            "hemtt_browse",
            "proj_browse",
            "arma3_browse",
            "btn_check",
            "btn_dev",
            "btn_launch",
            "btn_build",
            "btn_release",
            "btn_cancel",
            "btn_ln_sort",
            "btn_ln_coverage",
            "btn_utils_fnl",
            "btn_utils_bom",
            "btn_book",
            "btn_paa_convert",
            "btn_paa_inspect",
            "btn_pbo_inspect",
            "btn_pbo_unpack",
            "btn_dark_mode",
            "btn_custom",
        ]
        # Apply style only to buttons that exist
        for attr_name in button_attrs:
            if hasattr(self, attr_name):
                button = getattr(self, attr_name)
                button.setStyleSheet(self.button_style)

    def _append_output(self, text: str):
        """Append a line to the output widget with basic severity highlighting."""
        # Detect log level and apply appropriate color
        text_lower = text.lower()
        color = None

        # Check for error patterns
        if any(
            pattern in text_lower for pattern in ["error", "err:", "fatal", "failed", "failure"]
        ):
            color = self.current_theme["error"].name()
        # Check for warning patterns
        elif any(pattern in text_lower for pattern in ["warning", "warn:", "caution"]):
            color = self.current_theme["warning"].name()
        # Check for info patterns
        elif any(pattern in text_lower for pattern in ["info", "information", "note:", "hint:"]):
            color = self.current_theme["info"].name()

        # Move cursor to end and insert text
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        if color:
            cursor.insertHtml(
                f'<span style="color: {color};">{text.replace("<", "&lt;").replace(">", "&gt;")}</span><br>'
            )
        else:
            # Ensure text ends with newline if not already present
            if not text.endswith("\n"):
                text += "\n"
            cursor.insertText(text)

        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _enqueue_output(self, text: str):
        """Queue text from the background runner for UI-thread insertion."""
        self.output_queue.put(text)

    def _poll_output_queue(self) -> None:
        """Drain the output queue periodically and update elapsed time."""
        try:
            while True:
                text = self.output_queue.get_nowait()
                self._append_output(text)
        except queue.Empty:
            pass
        if self.running and self.start_time:
            elapsed = time.time() - self.start_time
            self.elapsed_label.setText(f"Elapsed: {elapsed:0.1f}s")
        else:
            self.elapsed_label.setText("")

    def _set_running(self, running: bool, command_str: str | None = None):
        """Enable/disable widgets and update status based on run state."""
        self.running = running
        widgets = [
            self.btn_build,
            self.btn_release,
            self.btn_check,
            self.btn_dev,
            self.btn_launch,
            self.btn_utils_fnl,
            self.btn_utils_bom,
            self.btn_ln_sort,
            self.btn_ln_coverage,
            self.btn_paa_convert,
            self.btn_paa_inspect,
            self.btn_pbo_inspect,
            self.btn_pbo_unpack,
            self.btn_install_hemtt,
            self.btn_update_hemtt,
            self.btn_custom,
            self.custom_entry,
        ]
        for w in widgets:
            w.setEnabled(not running)

        self.btn_cancel.setEnabled(running)

        if running:
            self.status_label.setText(f"Running: {command_str}")
            self.start_time = time.time()
        else:
            self.status_label.setText("Ready")
            self.start_time = 0.0

    def _validated_paths(self) -> tuple[str, str] | None:
        """Validate and resolve the HEMTT executable and project directory.

        Returns a tuple of (hemtt_path, project_dir) when valid, or None if
        validation fails and the user cancels.
        """
        hemtt = self.hemtt_entry.text().strip() or "hemtt"
        proj = self.proj_entry.text().strip() or os.getcwd()

        if not os.path.isdir(proj):
            QMessageBox.critical(self, APP_TITLE, f"Project directory not found:\n{proj}")
            return None

        # If hemtt is not an explicit path, allow PATH resolution
        if (
            os.path.sep in hemtt or (os.path.altsep and os.path.altsep in hemtt)
        ) and not os.path.isfile(hemtt):
            QMessageBox.critical(self, APP_TITLE, f"HEMTT executable not found:\n{hemtt}")
            return None
        elif os.path.sep not in hemtt and (not os.path.altsep or os.path.altsep not in hemtt):
            resolved = shutil.which(hemtt)
            if resolved is None:
                # Still allow to try, but warn user
                reply = QMessageBox.question(
                    self,
                    APP_TITLE,
                    "'hemtt' not found in PATH. Continue anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return None
        return hemtt, proj

    def _run(self, args: list[str], command_type: str = "other", cwd: str | None = None):
        """Start running a HEMTT command with arguments from dialogs.

        Parameters
        ----------
        args: list[str]
            Full arguments after the 'hemtt' executable, including all flags.
        command_type: str
            Type of command for tracking purposes.
        cwd: str | None
            Optional working directory. If None, uses project directory.
        """
        validated = self._validated_paths()
        if not validated:
            return
        hemtt, proj = validated

        # Use provided cwd or default to project directory
        working_dir = cwd if cwd is not None else proj

        # Clear output and persist config
        self.output.clear()
        self._persist_config()

        cmd = build_command(hemtt, args)
        self._set_running(True, " ".join(cmd))

        self.runner = CommandRunner(
            command=cmd,
            cwd=working_dir,
            on_output=self._enqueue_output,
            on_exit=self._on_command_exit,
        )
        self.runner.start()

    def _on_command_exit(self, returncode: int):
        """Handle process termination and update UI state."""
        self._enqueue_output(f"\n[Process exited with code {returncode}]\n")
        self._set_running(False)
        self.runner = None

    def _cancel_run(self) -> None:
        """Request cancellation of the running process, if any."""
        if self.runner:
            self.runner.cancel()
            self._enqueue_output("\n[Cancellation requested]\n")

    # Button handlers
    def _run_build(self) -> None:
        """Open build dialog and run hemtt build with selected options."""
        # Temporarily simplified - run with no args
        self._run(["build"], command_type="build")

    def _run_release(self) -> None:
        """Open release dialog and run hemtt release with selected options."""
        # Temporarily simplified - run with no args
        self._run(["release"], command_type="release")

    def _run_check(self) -> None:
        """Open check dialog and run hemtt check with selected options."""
        # Temporarily simplified - run with no args
        self._run(["check"], command_type="check")

    def _run_dev(self) -> None:
        """Open dev dialog and run hemtt dev with selected options."""
        # Temporarily simplified - run with no args
        self._run(["dev"], command_type="dev")

    def _run_utils_fnl(self) -> None:
        """Run 'hemtt utils fnl'."""
        self._run(["utils", "fnl"], command_type="other")

    def _run_utils_bom(self) -> None:
        """Run 'hemtt utils bom'."""
        self._run(["utils", "bom"], command_type="other")

    def _run_ln_sort(self) -> None:
        """Run 'hemtt ln sort'."""
        self._run(["ln", "sort"], command_type="other")

    def _run_ln_coverage(self) -> None:
        """Run 'hemtt ln coverage'."""
        self._run(["ln", "coverage"], command_type="other")

    def _run_paa_convert(self) -> None:
        """Open PAA convert dialog and run hemtt utils paa convert with selected files."""
        # Temporarily use file dialog
        src_file, _ = QFileDialog.getOpenFileName(self, "Select source file", "", "All files (*.*)")
        if src_file:
            dest_file, _ = QFileDialog.getSaveFileName(
                self, "Select destination file", "", "All files (*.*)"
            )
            if dest_file:
                args = ["utils", "paa", "convert", src_file, dest_file]
                src_dir = os.path.dirname(os.path.abspath(src_file))
                self._run(args, command_type="other", cwd=src_dir)

    def _run_paa_inspect(self) -> None:
        """Open PAA inspect dialog and run hemtt utils paa inspect with selected options."""
        self._run_file_operation("PAA", "*.paa", ["utils", "paa", "inspect"])

    def _run_pbo_inspect(self) -> None:
        """Open PBO inspect dialog and run hemtt utils pbo inspect with selected options."""
        self._run_file_operation("PBO", "*.pbo", ["utils", "pbo", "inspect"])

    def _run_pbo_unpack(self) -> None:
        """Open PBO unpack dialog and run hemtt utils pbo unpack with selected options."""
        self._run_file_operation("PBO", "*.pbo", ["utils", "pbo", "unpack"])

    def _run_file_operation(
        self, file_type: str, filter_pattern: str, base_args: list[str]
    ) -> None:
        """Helper method for file-based operations (PAA/PBO inspect/unpack).

        Parameters
        ----------
        file_type : str
            Human-readable file type (e.g., "PAA", "PBO")
        filter_pattern : str
            File filter pattern (e.g., "*.paa", "*.pbo")
        base_args : list[str]
            Base command arguments before the filename
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {file_type} file", "", f"{file_type} files ({filter_pattern})"
        )
        if file_path:
            args = base_args + [file_path]
            file_dir = os.path.dirname(os.path.abspath(file_path))
            self._run(args, command_type="other", cwd=file_dir)

    def _run_custom(self) -> None:
        """Run a custom argument list typed by the user after 'hemtt'."""
        extra = self.custom_entry.text().strip()
        if not extra:
            QMessageBox.information(self, APP_TITLE, "Enter custom arguments, e.g. 'validate'")
            return
        args = [a for a in extra.split(" ") if a]
        self._run(args, command_type="other")

    def _install_hemtt(self) -> None:
        """Install HEMTT via winget (BrettMayson.HEMTT)."""
        self._run_winget(["install", "--id", "BrettMayson.HEMTT", "-e"], label="winget install")

    def _update_hemtt(self) -> None:
        """Update/upgrade HEMTT via winget (BrettMayson.HEMTT)."""
        self._run_winget(["upgrade", "--id", "BrettMayson.HEMTT", "-e"], label="winget upgrade")

    def _run_winget(self, winget_args: list[str], label: str) -> None:
        """Run a winget command and stream output to the console.

        Parameters
        ----------
        winget_args: list[str]
            Arguments after 'winget'. Example: ['install', '--id', 'BrettMayson.HEMTT', '-e']
        label: str
            Short label for status bar.
        """
        # Clear output
        self.output.clear()

        cmd = ["winget", *winget_args]
        self._set_running(True, " ".join(cmd))

        self.runner = CommandRunner(
            command=cmd,
            cwd=os.getcwd(),
            on_output=self._enqueue_output,
            on_exit=self._on_command_exit,
        )
        self.runner.start()

    def _run_launch(self) -> None:
        """Open launch dialog and run hemtt launch with selected options."""
        # Temporarily simplified - run with no args
        self._run(["launch"], command_type="launch")

    def _open_book(self) -> None:
        """Open the HEMTT documentation in the default web browser."""
        try:
            webbrowser.open("https://hemtt.dev")
        except Exception as e:
            QMessageBox.critical(self, APP_TITLE, f"Failed to open browser:\n{e}")

    def closeEvent(self, event):
        """Prompt on close if a command is running, then persist and exit."""
        if self.runner and self.runner.is_running:
            reply = QMessageBox.question(
                self,
                APP_TITLE,
                "A command is still running. Exit anyway?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        self._persist_config()
        event.accept()


# Dialog classes temporarily removed - dialogs simplified to use basic file pickers
# TODO: Rebuild dialog classes using PySide6 QDialog
#
# Main commands (check, dev, build, release, launch) now run with default arguments
# File-based commands (PAA/PBO tools) use simple file dialogs
#
# To restore full functionality, rebuild these dialog classes using PySide6 widgets:
# - CheckDialog, DevDialog, BuildDialog, ReleaseDialog, LaunchDialog
# - PaaConvertDialog, PaaInspectDialog, PboInspectDialog, PboUnpackDialog


def main() -> None:
    """Entrypoint to start the PySide6 application."""
    app = QApplication(sys.argv)
    window = HemttGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
