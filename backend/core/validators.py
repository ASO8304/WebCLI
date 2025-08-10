"""
Central validation router.

Each config file gets its own module under core/validators_files/<name>.py
Inside that module, define TWO functions per (section, key):

    help_<section>_<key>() -> str
    validate_<section>_<key>(value: str) -> bool | (bool, str)

Example:
    def help_CatSleep_Sleep(): ...
    def validate_CatSleep_Sleep(value: str): ...

Section/key names are normalized to function names by:
  - converting to lowercase
  - replacing non-alphanumeric with underscores
  - collapsing multiple underscores
  - stripping leading/trailing underscores
  - prepending '_' if it starts with a digit

Public API used by config_manager:
    validate_param(file_name, section, key, value) -> (ok: bool, message: str)
    help_for(file_name, section, key) -> Optional[str]
"""

from __future__ import annotations

import importlib
import re
from typing import Dict, Optional, Tuple, Any

# Map config file names to their validator module path.
# Left side must match keys in CONFIG_MAP in config_manager.py
FILE_MODULES: Dict[str, str] = {
    "settings.test": "core.validators_files.settings_test",
    # Add your other files here:
    # "example.ini": "core.validators_files.example_ini",
    # "custom_config.json": "core.validators_files.custom_config",
}

_loaded: Dict[str, Any] = {}


def _load_module_for(file_name: str):
    if file_name in _loaded:
        return _loaded[file_name]
    mod_path = FILE_MODULES.get(file_name)
    if not mod_path:
        _loaded[file_name] = None
        return None
    try:
        mod = importlib.import_module(mod_path)
        _loaded[file_name] = mod
        return mod
    except Exception:
        _loaded[file_name] = None
        return None


def _mangle(name: str) -> str:
    s = re.sub(r"[^0-9A-Za-z]+", "_", str(name))
    s = re.sub(r"_+", "_", s).strip("_").lower()
    if not s:
        s = "x"
    if s[0].isdigit():
        s = "_" + s
    return s


def _func_name(prefix: str, section: str, key: str) -> str:
    return f"{prefix}_{_mangle(section)}_{_mangle(key)}"


def help_for(file_name: str, section: str, key: str) -> Optional[str]:
    """Return a short, user-facing help string for this (file, section, key), or None."""
    mod = _load_module_for(file_name)
    if not mod:
        return None
    fn_name = _func_name("help", section, key)
    fn = getattr(mod, fn_name, None)
    if not callable(fn):
        return None
    try:
        txt = fn()
        return str(txt) if txt is not None else None
    except Exception:
        return None


def validate_param(file_name: str, section: str, key: str, value: str) -> Tuple[bool, str]:
    """
    Validate value for (file, section, key).
    The per-file function may return:
        - bool
        - (bool, message)
    When invalid and no custom message, we append the help text if available.
    """
    mod = _load_module_for(file_name)
    if not mod:
        return False, f"No validator module registered for file '{file_name}'."

    fn_name = _func_name("validate", section, key)
    fn = getattr(mod, fn_name, None)
    if not callable(fn):
        return False, f"No validator for [{section}].{key} in '{file_name}'."

    try:
        res = fn(value)
    except Exception as ex:
        return False, f"Validation error for [{section}].{key}: {ex}"

    if isinstance(res, tuple):
        ok = bool(res[0])
        msg = str(res[1]) if len(res) > 1 and res[1] is not None else ""
    else:
        ok = bool(res)
        msg = ""

    if ok:
        return True, ""

    # Invalid: if no custom message, fall back to help
    if not msg:
        h = help_for(file_name, section, key)
        if h:
            msg = f"Invalid value. {h}"
        else:
            msg = "Invalid value."
    return False, msg
