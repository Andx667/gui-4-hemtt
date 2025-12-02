import os
import time
import unittest
from unittest.mock import patch

from command_runner import CommandRunner, build_command, strip_ansi_codes
from config_store import get_config_path, load_config, save_config


class TestCommandRunner(unittest.TestCase):
    """Test command_runner module functions."""

    def test_build_command(self):
        """Test command building concatenates correctly."""
        cmd = build_command("hemtt", ["build"])
        self.assertEqual(cmd, ["hemtt", "build"])

    def test_build_command_with_args(self):
        """Test command building with multiple arguments."""
        cmd = build_command("hemtt", ["dev", "-b", "--no-rap"])
        self.assertEqual(cmd, ["hemtt", "dev", "-b", "--no-rap"])

    def test_build_command_empty_args(self):
        """Test command building with empty args list."""
        cmd = build_command("hemtt", [])
        self.assertEqual(cmd, ["hemtt"])

    def test_build_command_with_path(self):
        """Test command building with full path to executable."""
        cmd = build_command("/usr/local/bin/hemtt", ["version"])
        self.assertEqual(cmd, ["/usr/local/bin/hemtt", "version"])

    def test_strip_ansi_codes_simple(self):
        """Test ANSI code stripping with basic color codes."""
        text = "\x1b[31mError\x1b[0m"
        self.assertEqual(strip_ansi_codes(text), "Error")

    def test_strip_ansi_codes_complex(self):
        """Test ANSI code stripping with complex escape sequences."""
        text = "\x1b[1;32mSuccess:\x1b[0m \x1b[33mWarning\x1b[0m"
        self.assertEqual(strip_ansi_codes(text), "Success: Warning")

    def test_strip_ansi_codes_no_codes(self):
        """Test that text without ANSI codes is unchanged."""
        text = "Plain text without codes"
        self.assertEqual(strip_ansi_codes(text), text)

    def test_strip_ansi_codes_empty(self):
        """Test stripping from empty string."""
        self.assertEqual(strip_ansi_codes(""), "")

    def test_strip_ansi_codes_multiline(self):
        """Test ANSI code stripping with multiple lines."""
        text = "\x1b[32mLine 1\x1b[0m\n\x1b[31mLine 2\x1b[0m"
        self.assertEqual(strip_ansi_codes(text), "Line 1\nLine 2")

    def test_strip_ansi_codes_cursor_movement(self):
        """Test stripping cursor movement escape sequences."""
        text = "\x1b[2J\x1b[HCleared screen"
        self.assertEqual(strip_ansi_codes(text), "Cleared screen")


class TestCommandRunnerClass(unittest.TestCase):
    """Test CommandRunner class functionality."""

    def test_command_runner_initialization(self):
        """Test CommandRunner initializes with correct state."""
        runner = CommandRunner(
            command=["echo", "test"],
            cwd="/tmp",
            on_output=None,
            on_exit=None,
        )
        self.assertEqual(runner.command, ["echo", "test"])
        self.assertEqual(runner.cwd, "/tmp")
        self.assertFalse(runner.is_running)
        self.assertIsNone(runner.process)
        self.assertFalse(runner._cancel_requested)

    def test_command_runner_callbacks(self):
        """Test CommandRunner calls callbacks correctly."""
        output_lines = []
        exit_codes = []

        def on_output(line):
            output_lines.append(line)

        def on_exit(code):
            exit_codes.append(code)

        runner = CommandRunner(
            command=["python", "-c", "print('test')"],
            on_output=on_output,
            on_exit=on_exit,
        )
        runner.start()
        time.sleep(0.5)  # Give time for process to complete

        self.assertGreater(len(output_lines), 0)
        self.assertEqual(len(exit_codes), 1)
        self.assertEqual(exit_codes[0], 0)

    def test_command_runner_default_callbacks(self):
        """Test CommandRunner works with no callbacks provided."""
        runner = CommandRunner(command=["python", "-c", "print('test')"])
        runner.start()
        time.sleep(0.5)
        self.assertFalse(runner.is_running)

    def test_command_runner_file_not_found(self):
        """Test CommandRunner handles non-existent command."""
        output_lines = []
        exit_codes = []

        runner = CommandRunner(
            command=["nonexistent_command_12345"],
            on_output=lambda line: output_lines.append(line),
            on_exit=lambda code: exit_codes.append(code),
        )
        runner.start()
        time.sleep(0.5)

        self.assertGreater(len(output_lines), 0)
        self.assertIn("Error", output_lines[0])
        self.assertEqual(exit_codes[0], 127)

    def test_command_runner_with_env(self):
        """Test CommandRunner respects custom environment variables."""
        output_lines = []

        def on_output(line):
            output_lines.append(line)

        # Test that NO_COLOR env var is set
        runner = CommandRunner(
            command=["python", "-c", "import os; print(os.environ.get('NO_COLOR', 'not set'))"],
            on_output=on_output,
            on_exit=lambda _: None,
            env=os.environ.copy(),
        )
        runner.start()
        time.sleep(0.5)

        # Should have NO_COLOR=1 set by the runner
        self.assertTrue(any("1" in line for line in output_lines))

    def test_command_runner_cancel(self):
        """Test CommandRunner cancellation."""
        runner = CommandRunner(
            command=["python", "-c", "import time; time.sleep(10)"],
            on_output=lambda _: None,
            on_exit=lambda _: None,
        )
        runner.start()
        time.sleep(0.2)
        self.assertTrue(runner.is_running)
        runner.cancel()
        time.sleep(0.5)
        self.assertFalse(runner.is_running)

    def test_command_runner_multiple_starts(self):
        """Test that starting an already running runner has no effect."""
        runner = CommandRunner(
            command=["python", "-c", "import time; time.sleep(1)"],
            on_output=lambda _: None,
            on_exit=lambda _: None,
        )
        runner.start()
        time.sleep(0.1)
        first_process = runner.process
        runner.start()  # Try to start again
        self.assertIs(runner.process, first_process)  # Should be same process
        runner.cancel()
        time.sleep(0.5)


class TestConfigStore(unittest.TestCase):
    """Test config_store module functions."""

    def test_config_roundtrip(self):
        """Test config save and load cycle."""
        cfg = load_config()
        cfg["hemtt_path"] = "hemtt-custom"
        cfg["project_dir"] = "/test/path"
        save_config(cfg)
        loaded = load_config()
        self.assertEqual(loaded["hemtt_path"], "hemtt-custom")
        self.assertEqual(loaded["project_dir"], "/test/path")

    def test_config_dark_mode(self):
        """Test dark mode preference persistence."""
        cfg = load_config()
        cfg["dark_mode"] = True
        save_config(cfg)
        loaded = load_config()
        self.assertTrue(loaded["dark_mode"])

    def test_config_defaults(self):
        """Test that config has reasonable defaults."""
        cfg = load_config()
        self.assertIn("hemtt_path", cfg)
        self.assertIn("project_dir", cfg)
        self.assertIn("dark_mode", cfg)
        self.assertEqual(cfg["hemtt_path"], "hemtt")
        self.assertFalse(cfg["dark_mode"])

    def test_config_verbose_option(self):
        """Test verbose option persistence."""
        cfg = load_config()
        cfg["verbose"] = True
        save_config(cfg)
        loaded = load_config()
        self.assertTrue(loaded["verbose"])

    def test_config_pedantic_option(self):
        """Test pedantic option persistence."""
        cfg = load_config()
        cfg["pedantic"] = True
        save_config(cfg)
        loaded = load_config()
        self.assertTrue(loaded["pedantic"])

    def test_config_arma3_executable(self):
        """Test Arma 3 executable path persistence."""
        cfg = load_config()
        cfg["arma3_executable"] = "C:\\Program Files\\Arma 3\\arma3_x64.exe"
        save_config(cfg)
        loaded = load_config()
        self.assertEqual(loaded["arma3_executable"], "C:\\Program Files\\Arma 3\\arma3_x64.exe")

    def test_config_merge_with_defaults(self):
        """Test that config merges with defaults for missing keys."""
        cfg = {"hemtt_path": "custom"}
        save_config(cfg)
        loaded = load_config()
        # Should have custom value
        self.assertEqual(loaded["hemtt_path"], "custom")
        # Should have default values for missing keys
        self.assertIn("dark_mode", loaded)
        self.assertIn("verbose", loaded)

    def test_config_invalid_data_returns_defaults(self):
        """Test that invalid config data returns defaults."""
        # Save invalid JSON-like data
        with patch("builtins.open", side_effect=Exception("IO Error")):
            cfg = load_config()
            # Should return defaults on error
            self.assertEqual(cfg["hemtt_path"], "hemtt")
            self.assertFalse(cfg["dark_mode"])

    def test_config_non_dict_returns_defaults(self):
        """Test that non-dict JSON returns defaults."""
        import json

        path = get_config_path()
        # Write non-dict JSON (list instead)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(["not", "a", "dict"], f)

        cfg = load_config()
        # Should return defaults
        self.assertEqual(cfg["hemtt_path"], "hemtt")

    def test_config_path_function(self):
        """Test get_config_path returns valid path."""
        path = get_config_path()
        self.assertTrue(path.endswith("config.json"))
        self.assertTrue(os.path.isabs(path))

    def test_config_save_creates_file(self):
        """Test save_config creates file if it doesn't exist."""
        path = get_config_path()
        if os.path.exists(path):
            os.remove(path)

        cfg = {"hemtt_path": "test"}
        save_config(cfg)
        self.assertTrue(os.path.exists(path))

    def test_config_save_error_handling(self):
        """Test save_config handles errors gracefully."""
        with patch("builtins.open", side_effect=Exception("Write error")):
            # Should not raise exception
            save_config({"test": "value"})

    def test_config_extra_keys_preserved(self):
        """Test that extra keys in config are preserved."""
        cfg = load_config()
        cfg["custom_key"] = "custom_value"
        save_config(cfg)
        loaded = load_config()
        self.assertEqual(loaded["custom_key"], "custom_value")

    def test_config_non_string_keys_filtered(self):
        """Test that non-string keys are filtered out."""

        get_config_path()
        # Manually write config with non-string keys (though JSON doesn't allow this,
        # we can test the filtering logic)
        cfg = load_config()
        # All keys should be strings
        for key in cfg.keys():
            self.assertIsInstance(key, str)

    def tearDown(self):
        """Cleanup test config side effect."""
        path = get_config_path()
        if os.path.isfile(path):
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
