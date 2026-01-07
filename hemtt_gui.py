import os
import queue
import shutil
import subprocess
import sys
import time
import webbrowser

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
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

        # Separator with title for project commands
        project_commands_label = QLabel("Project Commands")
        project_commands_label.setFont(font)
        main_layout.addWidget(project_commands_label)

        separator_proj = QFrame()
        separator_proj.setFrameShape(QFrame.HLine)
        separator_proj.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator_proj)

        # Project commands frame
        project_btns_layout = QHBoxLayout()

        self.btn_new = QPushButton("hemtt new")
        self.btn_new.setStyleSheet(self.button_style)
        self.btn_new.setToolTip("Create a new HEMTT project\nInteractively sets up project structure")
        self.btn_new.clicked.connect(self._run_new)

        self.btn_license = QPushButton("hemtt license")
        self.btn_license.setStyleSheet(self.button_style)
        self.btn_license.setToolTip("Add or update license file\nChoose from available licenses")
        self.btn_license.clicked.connect(self._run_license)

        self.btn_script = QPushButton("hemtt script")
        self.btn_script.setStyleSheet(self.button_style)
        self.btn_script.setToolTip("Run a Rhai script\nExecute custom automation scripts")
        self.btn_script.clicked.connect(self._run_script)

        self.btn_value = QPushButton("hemtt value")
        self.btn_value.setStyleSheet(self.button_style)
        self.btn_value.setToolTip("Print config value\nRetrieve values from project configuration")
        self.btn_value.clicked.connect(self._run_value)

        self.btn_keys_generate = QPushButton("hemtt keys generate")
        self.btn_keys_generate.setStyleSheet(self.button_style)
        self.btn_keys_generate.setToolTip("Generate a new private key\nCreate keys for signing PBOs")
        self.btn_keys_generate.clicked.connect(self._run_keys_generate)

        project_btns_layout.addWidget(self.btn_new)
        project_btns_layout.addWidget(self.btn_license)
        project_btns_layout.addWidget(self.btn_script)
        project_btns_layout.addWidget(self.btn_value)
        project_btns_layout.addWidget(self.btn_keys_generate)
        project_btns_layout.addStretch()
        main_layout.addLayout(project_btns_layout)

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
        dialog = BuildDialog(self, self.dark_mode)
        if dialog.exec() == QDialog.Accepted:
            args = dialog.get_args()
            self._run(args, command_type="build")

    def _run_release(self) -> None:
        """Open release dialog and run hemtt release with selected options."""
        dialog = ReleaseDialog(self, self.dark_mode)
        if dialog.exec() == QDialog.Accepted:
            args = dialog.get_args()
            self._run(args, command_type="release")

    def _run_check(self) -> None:
        """Open check dialog and run hemtt check with selected options."""
        dialog = CheckDialog(self, self.dark_mode)
        if dialog.exec() == QDialog.Accepted:
            args = dialog.get_args()
            self._run(args, command_type="check")

    def _run_dev(self) -> None:
        """Open dev dialog and run hemtt dev with selected options."""
        dialog = DevDialog(self, self.dark_mode)
        if dialog.exec() == QDialog.Accepted:
            args = dialog.get_args()
            self._run(args, command_type="dev")

    def _run_utils_fnl(self) -> None:
        """Run 'hemtt utils fnl'."""
        self._run(["utils", "fnl"], command_type="other")

    def _run_utils_bom(self) -> None:
        """Run 'hemtt utils bom'."""
        self._run(["utils", "bom"], command_type="other")

    def _run_ln_sort(self) -> None:
        """Run 'hemtt localization sort'."""
        dialog = LocalizationSortDialog(self, self.dark_mode)
        if dialog.exec() == QDialog.Accepted:
            args = dialog.get_args()
            self._run(args, command_type="other")

    def _run_ln_coverage(self) -> None:
        """Run 'hemtt localization coverage'."""
        dialog = LocalizationCoverageDialog(self, self.dark_mode)
        if dialog.exec() == QDialog.Accepted:
            args = dialog.get_args()
            self._run(args, command_type="other")

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

    def _run_new(self) -> None:
        """Run 'hemtt new <name>' to create a new project in a terminal."""
        name, ok = self._get_text_input(
            "Create New Project",
            "Enter project name (folder will be created in current directory):",
            "my_mod"
        )
        if ok and name:
            # hemtt new is interactive, needs terminal
            self._run_in_terminal(["new", name], "Create new project")

    def _run_license(self) -> None:
        """Run 'hemtt license [name]' to add/update license."""
        from PySide6.QtWidgets import QInputDialog

        licenses = ["apl-sa", "apl", "apl-nd", "apache", "gpl", "mit", "unlicense", "interactive"]
        license_name, ok = QInputDialog.getItem(
            self,
            "Select License",
            "Choose a license (or 'interactive' to select interactively):",
            licenses,
            0,
            False
        )
        if ok:
            if license_name == "interactive":
                # Interactive mode needs terminal
                self._run_in_terminal(["license"], "Select license interactively")
            else:
                # Non-interactive with specific license can run in background
                self._run(["license", license_name], command_type="other")

    def _run_script(self) -> None:
        """Run 'hemtt script <name>' to execute a Rhai script."""
        name, ok = self._get_text_input(
            "Run Script",
            "Enter script name (without .rhai extension):",
            "my_script"
        )
        if ok and name:
            self._run(["script", name], command_type="other")

    def _run_value(self) -> None:
        """Run 'hemtt value <name>' to print a config value."""
        name, ok = self._get_text_input(
            "Get Config Value",
            "Enter config key (e.g., project.name, project.version):",
            "project.name"
        )
        if ok and name:
            self._run(["value", name], command_type="other")

    def _run_keys_generate(self) -> None:
        """Run 'hemtt keys generate' to create a new private key."""
        reply = QMessageBox.question(
            self,
            "Generate Private Key",
            "This will generate a new HEMTT private key.\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._run(["keys", "generate"], command_type="other")

    def _get_text_input(self, title: str, label: str, default: str = "") -> tuple[str, bool]:
        """Helper to get text input from user."""
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, title, label, QLineEdit.Normal, default)
        return text.strip(), ok

    def _run_in_terminal(self, args: list[str], description: str) -> None:
        """Run a HEMTT command in a new terminal window for interactive commands.

        Parameters
        ----------
        args : list[str]
            Arguments to pass to hemtt (e.g., ["new", "my_mod"])
        description : str
            Description of what the command does
        """
        hemtt_exe = self.hemtt_entry.text().strip() or "hemtt"
        project_dir = self.proj_entry.text().strip()

        # Build the full command
        cmd_parts = [hemtt_exe] + args
        cmd_str = " ".join(cmd_parts)

        # Determine working directory
        cwd = project_dir if project_dir and os.path.isdir(project_dir) else os.getcwd()

        # Show info message
        QMessageBox.information(
            self,
            APP_TITLE,
            f"Opening terminal to {description}.\n\n"
            f"Command: {cmd_str}\n"
            f"Working directory: {cwd}\n\n"
            f"The terminal window will open separately."
        )

        # Platform-specific terminal launching
        try:
            if sys.platform == "win32":
                # Windows: Use PowerShell or cmd
                # Keep terminal open after command with -NoExit for PowerShell
                terminal_cmd = [
                    "powershell.exe",
                    "-NoExit",
                    "-Command",
                    f"cd '{cwd}'; Write-Host 'Running: {cmd_str}' -ForegroundColor Cyan; {cmd_str}; Write-Host 'Command completed. You can close this window.' -ForegroundColor Green"
                ]
                subprocess.Popen(
                    terminal_cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=cwd
                )
            elif sys.platform == "darwin":
                # macOS: Use Terminal.app
                script = f'cd "{cwd}" && {cmd_str} && echo "Command completed. Press any key to close..." && read -n 1'
                subprocess.Popen(
                    ["osascript", "-e", f'tell app "Terminal" to do script "{script}"']
                )
            else:
                # Linux: Try common terminal emulators
                terminals = ["gnome-terminal", "konsole", "xterm"]
                cmd = f'cd "{cwd}" && {cmd_str} && echo "Command completed. Press Enter to close..." && read'

                launched = False
                for term in terminals:
                    try:
                        if term == "gnome-terminal":
                            subprocess.Popen([term, "--", "bash", "-c", cmd])
                        elif term == "konsole":
                            subprocess.Popen([term, "-e", "bash", "-c", cmd])
                        else:
                            subprocess.Popen([term, "-e", "bash", "-c", cmd])
                        launched = True
                        break
                    except FileNotFoundError:
                        continue

                if not launched:
                    raise Exception("No suitable terminal emulator found")

        except Exception as e:
            QMessageBox.critical(
                self,
                APP_TITLE,
                f"Failed to open terminal:\n{e}\n\n"
                f"Please run this command manually in a terminal:\n"
                f"cd {cwd}\n{cmd_str}"
            )

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
        dialog = LaunchDialog(self, self.dark_mode)
        if dialog.exec() == QDialog.Accepted:
            args = dialog.get_args()
            self._run(args, command_type="launch")

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


# =============================================================================
# Command Dialog Classes
# =============================================================================


class BaseCommandDialog(QDialog):
    """Base class for command dialogs with common widgets and styling."""

    def __init__(self, parent, title: str, dark_mode: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.dark_mode = dark_mode
        self.main_layout = QVBoxLayout(self)

        # Apply dark mode styling if needed
        if dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #2b2b2b; color: #e0e0e0; }
                QLabel { color: #e0e0e0; }
                QCheckBox { color: #e0e0e0; }
                QRadioButton { color: #e0e0e0; }
                QGroupBox { color: #e0e0e0; border: 1px solid #555; border-radius: 4px; margin-top: 8px; padding-top: 8px; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
                QLineEdit { background-color: #3b3b3b; color: #e0e0e0; border: 1px solid #555; border-radius: 3px; padding: 4px; }
                QComboBox { background-color: #3b3b3b; color: #e0e0e0; border: 1px solid #555; border-radius: 3px; padding: 4px; }
                QSpinBox { background-color: #3b3b3b; color: #e0e0e0; border: 1px solid #555; border-radius: 3px; padding: 4px; }
            """)

    def add_verbosity_section(self):
        """Add verbosity radio buttons (Normal/-v/-vv)."""
        verbosity_group = QGroupBox("Verbosity")
        verbosity_layout = QVBoxLayout()

        self.verbosity_normal = QRadioButton("Normal (default)")
        self.verbosity_debug = QRadioButton("Debug (-v)")
        self.verbosity_trace = QRadioButton("Trace (-vv)")
        self.verbosity_normal.setChecked(True)

        verbosity_layout.addWidget(self.verbosity_normal)
        verbosity_layout.addWidget(self.verbosity_debug)
        verbosity_layout.addWidget(self.verbosity_trace)
        verbosity_group.setLayout(verbosity_layout)

        self.main_layout.addWidget(verbosity_group)
        return verbosity_group

    def add_threads_section(self):
        """Add threads spinner."""
        threads_layout = QHBoxLayout()
        threads_label = QLabel("Threads:")
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setMinimum(1)
        self.threads_spinbox.setMaximum(128)
        self.threads_spinbox.setValue(os.cpu_count() or 4)
        self.threads_spinbox.setSpecialValueText("Default (auto)")
        threads_layout.addWidget(threads_label)
        threads_layout.addWidget(self.threads_spinbox)
        threads_layout.addStretch()

        self.main_layout.addLayout(threads_layout)
        return threads_layout

    def add_buttons(self):
        """Add standard OK/Cancel buttons."""
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.main_layout.addWidget(buttons)
        return buttons

    def get_verbosity_args(self) -> list[str]:
        """Get verbosity arguments based on selection."""
        if self.verbosity_debug.isChecked():
            return ["-v"]
        elif self.verbosity_trace.isChecked():
            return ["-vv"]
        return []

    def get_threads_args(self) -> list[str]:
        """Get threads arguments if not default."""
        threads = self.threads_spinbox.value()
        if threads != (os.cpu_count() or 4):
            return ["-t", str(threads)]
        return []


class CheckDialog(BaseCommandDialog):
    """Dialog for 'hemtt check' command options."""

    def __init__(self, parent, dark_mode: bool = False):
        super().__init__(parent, "HEMTT Check Options", dark_mode)

        # Options
        options_group = QGroupBox("Check Options")
        options_layout = QVBoxLayout()

        self.pedantic_check = QCheckBox("Pedantic mode (-p)")
        self.pedantic_check.setToolTip("Enable all lints that are disabled by default")

        self.error_on_all_check = QCheckBox("Treat warnings as errors (-e)")
        self.error_on_all_check.setToolTip("Treat all help and warning messages as errors")

        options_layout.addWidget(self.pedantic_check)
        options_layout.addWidget(self.error_on_all_check)

        # Custom lints
        lints_layout = QHBoxLayout()
        lints_label = QLabel("Custom lints (-L):")
        self.lints_entry = QLineEdit()
        self.lints_entry.setPlaceholderText("e.g., s01-invalid-command s02-unknown-command")
        lints_layout.addWidget(lints_label)
        lints_layout.addWidget(self.lints_entry)
        options_layout.addLayout(lints_layout)

        options_group.setLayout(options_layout)
        self.main_layout.addWidget(options_group)

        # Verbosity and threads
        self.add_verbosity_section()
        self.add_threads_section()
        self.add_buttons()

    def get_args(self) -> list[str]:
        """Build argument list from dialog selections."""
        args = ["check"]

        if self.pedantic_check.isChecked():
            args.append("-p")

        if self.error_on_all_check.isChecked():
            args.append("-e")

        # Add custom lints
        lints_text = self.lints_entry.text().strip()
        if lints_text:
            for lint in lints_text.split():
                args.extend(["-L", lint])

        args.extend(self.get_threads_args())
        args.extend(self.get_verbosity_args())

        return args


class DevDialog(BaseCommandDialog):
    """Dialog for 'hemtt dev' command options."""

    def __init__(self, parent, dark_mode: bool = False):
        super().__init__(parent, "HEMTT Dev Options", dark_mode)

        # Build options
        build_group = QGroupBox("Build Options")
        build_layout = QVBoxLayout()

        self.binarize_check = QCheckBox("Binarize (-b)")
        self.binarize_check.setToolTip("Use BI's binarize on supported files")

        self.no_rap_check = QCheckBox("No rapify (--no-rap)")
        self.no_rap_check.setToolTip("Do not rapify (cpp, rvmat, ext, sqm, bikb, bisurf)")

        build_layout.addWidget(self.binarize_check)
        build_layout.addWidget(self.no_rap_check)
        build_group.setLayout(build_layout)
        self.main_layout.addWidget(build_group)

        # Optionals
        optionals_group = QGroupBox("Optional Addons")
        optionals_layout = QVBoxLayout()

        self.all_optionals_check = QCheckBox("Include all optionals (-O)")
        self.all_optionals_check.setToolTip("Include all optional addon folders")
        optionals_layout.addWidget(self.all_optionals_check)

        specific_layout = QHBoxLayout()
        specific_label = QLabel("Specific optionals (-o):")
        self.optionals_entry = QLineEdit()
        self.optionals_entry.setPlaceholderText("e.g., caramel chocolate")
        specific_layout.addWidget(specific_label)
        specific_layout.addWidget(self.optionals_entry)
        optionals_layout.addLayout(specific_layout)

        optionals_group.setLayout(optionals_layout)
        self.main_layout.addWidget(optionals_group)

        # Just addons
        just_layout = QHBoxLayout()
        just_label = QLabel("Build only (--just):")
        self.just_entry = QLineEdit()
        self.just_entry.setPlaceholderText("e.g., myAddon1 myAddon2")
        just_layout.addWidget(just_label)
        just_layout.addWidget(self.just_entry)
        self.main_layout.addLayout(just_layout)

        # Verbosity and threads
        self.add_verbosity_section()
        self.add_threads_section()
        self.add_buttons()

    def get_args(self) -> list[str]:
        """Build argument list from dialog selections."""
        args = ["dev"]

        if self.binarize_check.isChecked():
            args.append("-b")

        if self.no_rap_check.isChecked():
            args.append("--no-rap")

        if self.all_optionals_check.isChecked():
            args.append("-O")

        # Specific optionals
        optionals_text = self.optionals_entry.text().strip()
        if optionals_text:
            for opt in optionals_text.split():
                args.extend(["-o", opt])

        # Just addons
        just_text = self.just_entry.text().strip()
        if just_text:
            for addon in just_text.split():
                args.extend(["--just", addon])

        args.extend(self.get_threads_args())
        args.extend(self.get_verbosity_args())

        return args


class BuildDialog(BaseCommandDialog):
    """Dialog for 'hemtt build' command options."""

    def __init__(self, parent, dark_mode: bool = False):
        super().__init__(parent, "HEMTT Build Options", dark_mode)

        # Build options
        options_group = QGroupBox("Build Options")
        options_layout = QVBoxLayout()

        self.no_bin_check = QCheckBox("No binarize (--no-bin)")
        self.no_bin_check.setToolTip("Do not binarize the project")

        self.no_rap_check = QCheckBox("No rapify (--no-rap)")
        self.no_rap_check.setToolTip("Do not rapify (cpp, rvmat, ext, sqm, bikb, bisurf)")

        options_layout.addWidget(self.no_bin_check)
        options_layout.addWidget(self.no_rap_check)
        options_group.setLayout(options_layout)
        self.main_layout.addWidget(options_group)

        # Just addons
        just_layout = QHBoxLayout()
        just_label = QLabel("Build only (--just):")
        self.just_entry = QLineEdit()
        self.just_entry.setPlaceholderText("e.g., myAddon1 myAddon2")
        just_layout.addWidget(just_label)
        just_layout.addWidget(self.just_entry)
        self.main_layout.addLayout(just_layout)

        # Verbosity and threads
        self.add_verbosity_section()
        self.add_threads_section()
        self.add_buttons()

    def get_args(self) -> list[str]:
        """Build argument list from dialog selections."""
        args = ["build"]

        if self.no_bin_check.isChecked():
            args.append("--no-bin")

        if self.no_rap_check.isChecked():
            args.append("--no-rap")

        # Just addons
        just_text = self.just_entry.text().strip()
        if just_text:
            for addon in just_text.split():
                args.extend(["--just", addon])

        args.extend(self.get_threads_args())
        args.extend(self.get_verbosity_args())

        return args


class ReleaseDialog(BaseCommandDialog):
    """Dialog for 'hemtt release' command options."""

    def __init__(self, parent, dark_mode: bool = False):
        super().__init__(parent, "HEMTT Release Options", dark_mode)

        # Release options
        options_group = QGroupBox("Release Options")
        options_layout = QVBoxLayout()

        self.no_bin_check = QCheckBox("No binarize (--no-bin)")
        self.no_bin_check.setToolTip("Do not binarize the project")

        self.no_rap_check = QCheckBox("No rapify (--no-rap)")
        self.no_rap_check.setToolTip("Do not rapify (cpp, rvmat, ext, sqm, bikb, bisurf)")

        self.no_sign_check = QCheckBox("No sign (--no-sign)")
        self.no_sign_check.setToolTip("Do not sign the PBOs or create a bikey")

        self.no_archive_check = QCheckBox("No archive (--no-archive)")
        self.no_archive_check.setToolTip("Do not create a zip archive of the release")

        options_layout.addWidget(self.no_bin_check)
        options_layout.addWidget(self.no_rap_check)
        options_layout.addWidget(self.no_sign_check)
        options_layout.addWidget(self.no_archive_check)
        options_group.setLayout(options_layout)
        self.main_layout.addWidget(options_group)

        # Verbosity and threads
        self.add_verbosity_section()
        self.add_threads_section()
        self.add_buttons()

    def get_args(self) -> list[str]:
        """Build argument list from dialog selections."""
        args = ["release"]

        if self.no_bin_check.isChecked():
            args.append("--no-bin")

        if self.no_rap_check.isChecked():
            args.append("--no-rap")

        if self.no_sign_check.isChecked():
            args.append("--no-sign")

        if self.no_archive_check.isChecked():
            args.append("--no-archive")

        args.extend(self.get_threads_args())
        args.extend(self.get_verbosity_args())

        return args


class LaunchDialog(BaseCommandDialog):
    """Dialog for 'hemtt launch' command options."""

    def __init__(self, parent, dark_mode: bool = False):
        super().__init__(parent, "HEMTT Launch Options", dark_mode)

        # Profile/Config
        profile_layout = QHBoxLayout()
        profile_label = QLabel("Profile(s):")
        self.profile_entry = QLineEdit()
        self.profile_entry.setPlaceholderText("e.g., default ace +ws (leave empty for default)")
        profile_layout.addWidget(profile_label)
        profile_layout.addWidget(self.profile_entry)
        self.main_layout.addLayout(profile_layout)

        # Launch options
        launch_group = QGroupBox("Launch Options")
        launch_layout = QVBoxLayout()

        self.quick_check = QCheckBox("Quick launch (-Q)")
        self.quick_check.setToolTip("Skip build step, launch last built version")

        self.no_filepatching_check = QCheckBox("No file patching (-F)")
        self.no_filepatching_check.setToolTip("Disable file patching")

        launch_layout.addWidget(self.quick_check)
        launch_layout.addWidget(self.no_filepatching_check)
        launch_group.setLayout(launch_layout)
        self.main_layout.addWidget(launch_group)

        # Build options for dev
        build_group = QGroupBox("Dev Build Options")
        build_layout = QVBoxLayout()

        self.binarize_check = QCheckBox("Binarize (-b)")
        self.binarize_check.setToolTip("Use BI's binarize on supported files")

        self.no_rap_check = QCheckBox("No rapify (--no-rap)")
        self.no_rap_check.setToolTip("Do not rapify files")

        build_layout.addWidget(self.binarize_check)
        build_layout.addWidget(self.no_rap_check)
        build_group.setLayout(build_layout)
        self.main_layout.addWidget(build_group)

        # Optionals
        optionals_group = QGroupBox("Optional Addons")
        optionals_layout = QVBoxLayout()

        self.all_optionals_check = QCheckBox("Include all optionals (-O)")
        optionals_layout.addWidget(self.all_optionals_check)

        specific_layout = QHBoxLayout()
        specific_label = QLabel("Specific optionals (-o):")
        self.optionals_entry = QLineEdit()
        self.optionals_entry.setPlaceholderText("e.g., caramel chocolate")
        specific_layout.addWidget(specific_label)
        specific_layout.addWidget(self.optionals_entry)
        optionals_layout.addLayout(specific_layout)

        optionals_group.setLayout(optionals_layout)
        self.main_layout.addWidget(optionals_group)

        # Executable and instances
        exec_layout = QHBoxLayout()
        exec_label = QLabel("Executable (-e):")
        self.executable_entry = QLineEdit()
        self.executable_entry.setPlaceholderText("e.g., arma3_x64 or full path")
        exec_layout.addWidget(exec_label)
        exec_layout.addWidget(self.executable_entry)
        self.main_layout.addLayout(exec_layout)

        instances_layout = QHBoxLayout()
        instances_label = QLabel("Instances (-i):")
        self.instances_spinbox = QSpinBox()
        self.instances_spinbox.setMinimum(1)
        self.instances_spinbox.setMaximum(10)
        self.instances_spinbox.setValue(1)
        instances_layout.addWidget(instances_label)
        instances_layout.addWidget(self.instances_spinbox)
        instances_layout.addStretch()
        self.main_layout.addLayout(instances_layout)

        # Passthrough args
        passthrough_layout = QHBoxLayout()
        passthrough_label = QLabel("Passthrough args:")
        self.passthrough_entry = QLineEdit()
        self.passthrough_entry.setPlaceholderText("Args after -- (e.g., -world=empty -window)")
        passthrough_layout.addWidget(passthrough_label)
        passthrough_layout.addWidget(self.passthrough_entry)
        self.main_layout.addLayout(passthrough_layout)

        # Just addons
        just_layout = QHBoxLayout()
        just_label = QLabel("Build only (--just):")
        self.just_entry = QLineEdit()
        self.just_entry.setPlaceholderText("e.g., myAddon1 myAddon2")
        just_layout.addWidget(just_label)
        just_layout.addWidget(self.just_entry)
        self.main_layout.addLayout(just_layout)

        # Verbosity and threads
        self.add_verbosity_section()
        self.add_threads_section()
        self.add_buttons()

    def get_args(self) -> list[str]:
        """Build argument list from dialog selections."""
        args = ["launch"]

        # Profile(s) come first
        profile_text = self.profile_entry.text().strip()
        if profile_text:
            args.extend(profile_text.split())

        # Executable
        executable_text = self.executable_entry.text().strip()
        if executable_text:
            args.extend(["-e", executable_text])

        # Instances
        instances = self.instances_spinbox.value()
        if instances > 1:
            args.extend(["-i", str(instances)])

        # Launch flags
        if self.quick_check.isChecked():
            args.append("-Q")

        if self.no_filepatching_check.isChecked():
            args.append("-F")

        # Optionals
        if self.all_optionals_check.isChecked():
            args.append("-O")

        optionals_text = self.optionals_entry.text().strip()
        if optionals_text:
            for opt in optionals_text.split():
                args.extend(["-o", opt])

        # Build options
        if self.binarize_check.isChecked():
            args.append("-b")

        if self.no_rap_check.isChecked():
            args.append("--no-rap")

        # Just addons
        just_text = self.just_entry.text().strip()
        if just_text:
            for addon in just_text.split():
                args.extend(["--just", addon])

        args.extend(self.get_threads_args())
        args.extend(self.get_verbosity_args())

        # Passthrough args go last after --
        passthrough_text = self.passthrough_entry.text().strip()
        if passthrough_text:
            args.append("--")
            args.extend(passthrough_text.split())

        return args


class LocalizationCoverageDialog(BaseCommandDialog):
    """Dialog for 'hemtt localization coverage' command options."""

    def __init__(self, parent, dark_mode: bool = False):
        super().__init__(parent, "Localization Coverage Options", dark_mode)

        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Output format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["ascii", "json", "pretty-json", "markdown"])
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        self.main_layout.addLayout(format_layout)

        self.add_buttons()

    def get_args(self) -> list[str]:
        """Build argument list from dialog selections."""
        args = ["localization", "coverage"]

        fmt = self.format_combo.currentText()
        if fmt != "ascii":  # ascii is default
            args.extend(["--format", fmt])

        return args


class LocalizationSortDialog(BaseCommandDialog):
    """Dialog for 'hemtt localization sort' command options."""

    def __init__(self, parent, dark_mode: bool = False):
        super().__init__(parent, "Localization Sort Options", dark_mode)

        # Options
        self.only_lang_check = QCheckBox("Only sort languages (--only-lang)")
        self.only_lang_check.setToolTip("Only sort the languages within keys, preserve order of packages/containers/keys")
        self.main_layout.addWidget(self.only_lang_check)

        self.add_buttons()

    def get_args(self) -> list[str]:
        """Build argument list from dialog selections."""
        args = ["localization", "sort"]

        if self.only_lang_check.isChecked():
            args.append("--only-lang")

        return args


def main() -> None:
    """Entrypoint to start the PySide6 application."""
    app = QApplication(sys.argv)
    window = HemttGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
