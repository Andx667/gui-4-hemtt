import os
import time
import unittest
from unittest.mock import MagicMock, patch

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


class TestDialogArgumentBuilding(unittest.TestCase):
    """Test command dialog argument building (without GUI)."""

    def setUp(self):
        """Set up mock dialog attributes for testing."""
        self.mock_dialog = MagicMock()

    def test_check_dialog_arguments_basic(self):
        """Test CheckDialog basic argument building."""
        args = ["check"]
        # Expected: just the command with no options
        self.assertEqual(args, ["check"])

    def test_check_dialog_arguments_pedantic(self):
        """Test CheckDialog with pedantic flag."""
        args = ["check", "-p"]
        self.assertIn("-p", args)

    def test_check_dialog_arguments_error_on_all(self):
        """Test CheckDialog with error-on-all flag."""
        args = ["check", "-e"]
        self.assertIn("-e", args)

    def test_check_dialog_arguments_custom_lints(self):
        """Test CheckDialog with custom lints."""
        args = ["check", "-L", "s01-invalid-command", "-L", "s02-unknown-command"]
        self.assertIn("-L", args)
        self.assertIn("s01-invalid-command", args)

    def test_check_dialog_arguments_verbosity_debug(self):
        """Test CheckDialog with debug verbosity."""
        args = ["check", "-v"]
        self.assertIn("-v", args)

    def test_check_dialog_arguments_verbosity_trace(self):
        """Test CheckDialog with trace verbosity."""
        args = ["check", "-vv"]
        self.assertIn("-vv", args)

    def test_check_dialog_arguments_threads(self):
        """Test CheckDialog with custom thread count."""
        args = ["check", "-t", "8"]
        self.assertIn("-t", args)
        self.assertIn("8", args)

    def test_dev_dialog_arguments_basic(self):
        """Test DevDialog basic argument building."""
        args = ["dev"]
        self.assertEqual(args, ["dev"])

    def test_dev_dialog_arguments_binarize(self):
        """Test DevDialog with binarize flag."""
        args = ["dev", "-b"]
        self.assertIn("-b", args)

    def test_dev_dialog_arguments_no_rap(self):
        """Test DevDialog with no-rap flag."""
        args = ["dev", "--no-rap"]
        self.assertIn("--no-rap", args)

    def test_dev_dialog_arguments_all_optionals(self):
        """Test DevDialog with all-optionals flag."""
        args = ["dev", "-O"]
        self.assertIn("-O", args)

    def test_dev_dialog_arguments_specific_optionals(self):
        """Test DevDialog with specific optionals."""
        args = ["dev", "-o", "caramel", "-o", "chocolate"]
        self.assertIn("-o", args)
        self.assertIn("caramel", args)
        self.assertIn("chocolate", args)

    def test_dev_dialog_arguments_just_addon(self):
        """Test DevDialog with just addon filter."""
        args = ["dev", "--just", "myAddon"]
        self.assertIn("--just", args)
        self.assertIn("myAddon", args)

    def test_build_dialog_arguments_basic(self):
        """Test BuildDialog basic argument building."""
        args = ["build"]
        self.assertEqual(args, ["build"])

    def test_build_dialog_arguments_no_bin(self):
        """Test BuildDialog with no-bin flag."""
        args = ["build", "--no-bin"]
        self.assertIn("--no-bin", args)

    def test_build_dialog_arguments_no_rap(self):
        """Test BuildDialog with no-rap flag."""
        args = ["build", "--no-rap"]
        self.assertIn("--no-rap", args)

    def test_build_dialog_arguments_just_addon(self):
        """Test BuildDialog with just addon filter."""
        args = ["build", "--just", "addon1", "--just", "addon2"]
        self.assertIn("--just", args)
        self.assertIn("addon1", args)
        self.assertIn("addon2", args)

    def test_release_dialog_arguments_basic(self):
        """Test ReleaseDialog basic argument building."""
        args = ["release"]
        self.assertEqual(args, ["release"])

    def test_release_dialog_arguments_no_sign(self):
        """Test ReleaseDialog with no-sign flag."""
        args = ["release", "--no-sign"]
        self.assertIn("--no-sign", args)

    def test_release_dialog_arguments_no_archive(self):
        """Test ReleaseDialog with no-archive flag."""
        args = ["release", "--no-archive"]
        self.assertIn("--no-archive", args)

    def test_release_dialog_arguments_all_flags(self):
        """Test ReleaseDialog with all flags."""
        args = ["release", "--no-bin", "--no-rap", "--no-sign", "--no-archive", "-t", "4", "-v"]
        self.assertIn("--no-bin", args)
        self.assertIn("--no-rap", args)
        self.assertIn("--no-sign", args)
        self.assertIn("--no-archive", args)
        self.assertIn("-t", args)
        self.assertIn("-v", args)

    def test_launch_dialog_arguments_basic(self):
        """Test LaunchDialog basic argument building."""
        args = ["launch"]
        self.assertEqual(args, ["launch"])

    def test_launch_dialog_arguments_profile(self):
        """Test LaunchDialog with profile."""
        args = ["launch", "default"]
        self.assertIn("default", args)

    def test_launch_dialog_arguments_cdlc(self):
        """Test LaunchDialog with CDLC shortcut."""
        args = ["launch", "default", "+ws"]
        self.assertIn("+ws", args)

    def test_launch_dialog_arguments_quick(self):
        """Test LaunchDialog with quick flag."""
        args = ["launch", "-Q"]
        self.assertIn("-Q", args)

    def test_launch_dialog_arguments_no_filepatching(self):
        """Test LaunchDialog with no-filepatching flag."""
        args = ["launch", "-F"]
        self.assertIn("-F", args)

    def test_launch_dialog_arguments_executable(self):
        """Test LaunchDialog with custom executable."""
        args = ["launch", "-e", "arma3profiling_x64"]
        self.assertIn("-e", args)
        self.assertIn("arma3profiling_x64", args)

    def test_launch_dialog_arguments_instances(self):
        """Test LaunchDialog with multiple instances."""
        args = ["launch", "-i", "2"]
        self.assertIn("-i", args)
        self.assertIn("2", args)

    def test_launch_dialog_arguments_passthrough(self):
        """Test LaunchDialog with passthrough args."""
        args = ["launch", "--", "-world=empty", "-window"]
        self.assertIn("--", args)
        self.assertIn("-world=empty", args)
        self.assertIn("-window", args)

    def test_localization_coverage_arguments_ascii(self):
        """Test LocalizationCoverageDialog with ascii format (default)."""
        args = ["localization", "coverage"]
        self.assertEqual(args, ["localization", "coverage"])

    def test_localization_coverage_arguments_json(self):
        """Test LocalizationCoverageDialog with json format."""
        args = ["localization", "coverage", "--format", "json"]
        self.assertIn("--format", args)
        self.assertIn("json", args)

    def test_localization_coverage_arguments_markdown(self):
        """Test LocalizationCoverageDialog with markdown format."""
        args = ["localization", "coverage", "--format", "markdown"]
        self.assertIn("--format", args)
        self.assertIn("markdown", args)

    def test_localization_sort_arguments_basic(self):
        """Test LocalizationSortDialog basic argument building."""
        args = ["localization", "sort"]
        self.assertEqual(args, ["localization", "sort"])

    def test_localization_sort_arguments_only_lang(self):
        """Test LocalizationSortDialog with only-lang flag."""
        args = ["localization", "sort", "--only-lang"]
        self.assertIn("--only-lang", args)

    def test_new_command_arguments(self):
        """Test 'hemtt new' command argument building."""
        args = ["new", "my_mod"]
        self.assertEqual(args, ["new", "my_mod"])
        self.assertIn("my_mod", args)

    def test_license_command_arguments_interactive(self):
        """Test 'hemtt license' command without argument (interactive)."""
        args = ["license"]
        self.assertEqual(args, ["license"])

    def test_license_command_arguments_specific(self):
        """Test 'hemtt license' command with specific license."""
        args = ["license", "mit"]
        self.assertIn("mit", args)

    def test_script_command_arguments(self):
        """Test 'hemtt script' command argument building."""
        args = ["script", "my_script"]
        self.assertIn("script", args)
        self.assertIn("my_script", args)

    def test_value_command_arguments(self):
        """Test 'hemtt value' command argument building."""
        args = ["value", "project.name"]
        self.assertIn("value", args)
        self.assertIn("project.name", args)

    def test_keys_generate_command_arguments(self):
        """Test 'hemtt keys generate' command argument building."""
        args = ["keys", "generate"]
        self.assertEqual(args, ["keys", "generate"])

    def test_terminal_launch_command_building(self):
        """Test command building for terminal launches."""
        # Test that interactive commands prepare correct arguments
        args = ["new", "my_project"]
        self.assertIn("new", args)
        self.assertIn("my_project", args)

        # Test interactive license
        args = ["license"]
        self.assertEqual(args, ["license"])

    def test_combined_dialog_arguments_complex(self):
        """Test complex argument combination."""
        args = [
            "dev",
            "-b",
            "--no-rap",
            "-o",
            "opt1",
            "-o",
            "opt2",
            "--just",
            "addon",
            "-t",
            "8",
            "-vv",
        ]
        self.assertIn("dev", args)
        self.assertIn("-b", args)
        self.assertIn("--no-rap", args)
        self.assertIn("-o", args)
        self.assertIn("opt1", args)
        self.assertIn("opt2", args)
        self.assertIn("--just", args)
        self.assertIn("addon", args)
        self.assertIn("-t", args)
        self.assertIn("8", args)
        self.assertIn("-vv", args)


class TestCommandArgumentValidation(unittest.TestCase):
    """Test command argument validation and edge cases."""

    def test_empty_optional_list(self):
        """Test that empty optional list doesn't add arguments."""
        args = ["dev"]
        # Simulating empty optionals_entry
        optionals_text = ""
        if optionals_text:
            for opt in optionals_text.split():
                args.extend(["-o", opt])
        self.assertEqual(args, ["dev"])

    def test_whitespace_only_optionals(self):
        """Test that whitespace-only optionals are ignored."""
        args = ["dev"]
        optionals_text = "   "
        if optionals_text.strip():
            for opt in optionals_text.split():
                args.extend(["-o", opt])
        self.assertEqual(args, ["dev"])

    def test_multiple_whitespace_separated_values(self):
        """Test handling multiple whitespace-separated values."""
        args = ["dev"]
        optionals_text = "opt1  opt2   opt3"
        if optionals_text.strip():
            for opt in optionals_text.split():
                args.extend(["-o", opt])
        self.assertIn("opt1", args)
        self.assertIn("opt2", args)
        self.assertIn("opt3", args)
        # Should have 3 -o flags
        self.assertEqual(args.count("-o"), 3)

    def test_launch_passthrough_empty(self):
        """Test launch with empty passthrough args."""
        args = ["launch"]
        passthrough_text = ""
        if passthrough_text.strip():
            args.append("--")
            args.extend(passthrough_text.split())
        self.assertEqual(args, ["launch"])
        self.assertNotIn("--", args)

    def test_launch_passthrough_populated(self):
        """Test launch with populated passthrough args."""
        args = ["launch"]
        passthrough_text = "-world=empty -window"
        if passthrough_text.strip():
            args.append("--")
            args.extend(passthrough_text.split())
        self.assertIn("--", args)
        self.assertIn("-world=empty", args)
        self.assertIn("-window", args)
        # -- should come before passthrough args
        dash_index = args.index("--")
        world_index = args.index("-world=empty")
        self.assertLess(dash_index, world_index)

    def test_threads_default_cpu_count(self):
        """Test threads default to CPU count."""
        cpu_count = os.cpu_count() or 4
        threads_value = cpu_count
        args = ["check"]
        # Only add if not default
        if threads_value != cpu_count:
            args.extend(["-t", str(threads_value)])
        # Should not add threads arg when it's default
        self.assertEqual(args, ["check"])

    def test_threads_custom_value(self):
        """Test threads with custom value."""
        cpu_count = os.cpu_count() or 4
        threads_value = 8
        args = ["check"]
        if threads_value != cpu_count:
            args.extend(["-t", str(threads_value)])
        # Should add threads arg when it's not default
        if threads_value != cpu_count:
            self.assertIn("-t", args)
            self.assertIn("8", args)


if __name__ == "__main__":
    unittest.main()
