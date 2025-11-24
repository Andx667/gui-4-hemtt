from __future__ import annotations

import os
import re
import subprocess
import threading
from collections.abc import Callable


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape sequences from a string.

    Parameters
    ----------
    text: str
        Raw line possibly containing terminal color codes.

    Returns
    -------
    str
        Cleaned line without escape sequences.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def build_command(hemtt_executable: str, args: list[str]) -> list[str]:
    """Construct the argv list for invoking HEMTT.

    Parameters
    ----------
    hemtt_executable: str
        Path or name of the hemtt executable.
    args: list[str]
        Positional arguments to pass to hemtt.

    Returns
    -------
    list[str]
        The full command suitable for subprocess APIs.
    """
    cmd = [hemtt_executable]
    cmd.extend(args)
    return cmd


class CommandRunner:
    def __init__(
        self,
        command: list[str],
        cwd: str | None = None,
        on_output: Callable[[str], None] | None = None,
        on_exit: Callable[[int], None] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize a background command runner.

        Parameters
        ----------
        command: list[str]
            The full command list to execute (argv style).
        cwd: Optional[str]
            Working directory for the process.
        on_output: Callable[[str], None] | None
            Callback invoked for each line of stdout/stderr merged stream.
        on_exit: Callable[[int], None] | None
            Callback invoked once process finishes with its return code.
        env: Optional[dict[str, str]]
            Environment overrides; merged with current process env.
        """
        self.command = command
        self.cwd = cwd
        self.on_output = on_output or (lambda _text: None)
        self.on_exit = on_exit or (lambda _code: None)
        self.env = env

        self.process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._cancel_requested = False
        self.is_running = False

    def start(self) -> None:
        """Start the command runner in a background thread."""
        if self.is_running:
            return
        self._cancel_requested = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Cancel the running process by terminating or killing it."""
        self._cancel_requested = True
        if self.process and self.is_running:
            try:
                self.process.terminate()
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

    def _run(self) -> None:
        """Internal method to execute the command in a subprocess."""
        self.is_running = True
        try:
            # Prepare environment to disable color output from HEMTT
            run_env = self.env.copy() if self.env else os.environ.copy()
            # Force NO_COLOR to disable ANSI color codes
            run_env["NO_COLOR"] = "1"
            # Also set other common env vars that disable colors
            run_env["TERM"] = "dumb"

            # Use universal_newlines/text True for str output with UTF-8 encoding
            self.process = subprocess.Popen(
                self.command,
                cwd=self.cwd or None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                env=run_env,
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                # Strip ANSI escape codes before sending to output
                clean_line = strip_ansi_codes(line)
                self.on_output(clean_line)
                if self._cancel_requested:
                    break
            # Ensure process completed
            returncode = self.process.wait()
            self.on_exit(returncode)
        except FileNotFoundError as e:
            self.on_output(f"Error: {e}\n")
            self.on_exit(127)
        except Exception as e:
            self.on_output(f"Unexpected error: {e}\n")
            self.on_exit(1)
        finally:
            self.is_running = False
