import os
import unittest

from command_runner import build_command, strip_ansi_codes
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
