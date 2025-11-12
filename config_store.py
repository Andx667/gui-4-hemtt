from __future__ import annotations
import json
import os
from typing import Any, Dict

DEFAULTS = {
    "hemtt_path": "hemtt",
    "project_dir": os.getcwd(),
    # UI preferences
    "dark_mode": False,
    # Option toggles
    "verbose": False,
    "pedantic": False,
}


def get_config_path() -> str:
    """Return the absolute path to the local configuration JSON file."""
    # Store alongside the app by default for simplicity
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "config.json")


def load_config() -> Dict[str, Any]:
    """Load configuration from disk or return defaults on failure.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing configuration values merged with DEFAULTS.
    """
    path = get_config_path()
    if not os.path.isfile(path):
        return DEFAULTS.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return DEFAULTS.copy()
            # fill defaults
            cfg = DEFAULTS.copy()
            cfg.update({k: v for k, v in data.items() if isinstance(k, str)})
            return cfg
    except Exception:
        return DEFAULTS.copy()


def save_config(data: Dict[str, Any]) -> None:
    """Persist the provided configuration dictionary to disk as JSON."""
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        # Best effort only
        pass
