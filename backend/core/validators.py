"""
Central validation router.

Each config file gets its own module under core/validators_files/<name>.py
Inside that module, define TWO functions per (section, key):

    help_<section>_<key>() -> str
    validate_<section>_<key>(value: str) -> bool | (bool, str)

Section/key -> function name rules:
- We sanitize names by replacing non-alphanumerics with '_' and collapsing repeats.
- We try a case-preserving function name FIRST, then a lowercase fallback.
  So both `validate_CatSleep_Sleep` and `validate_catsleep_sleep` are accepted.
"""

from __future__ import annotations

import importlib
import re
import ipaddress
from typing import Dict, Optional, Tuple, Any, List, Callable

# Map config file names to their validator module path.
FILE_MODULES: Dict[str, str] = {
    "settings.test": "core.validators_files.settings_test",
    # Add more here:
    # "example.ini": "core.validators_files.example_ini",
    # "custom_config.json": "core.validators_files.custom_config",
}

_loaded: Dict[str, Any] = {}

# ---------------------------
# Common primitive validators
# ---------------------------

def validate_boolean(value: str) -> bool:
    return value.lower() in {"true", "false"}

def validate_integer(value: str) -> bool:
    return re.fullmatch(r"[+-]?\d+", value) is not None

def validate_nonempty_string(value: str) -> bool:
    return isinstance(value, str) and value.strip() != ""

def validate_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False

def validate_enum(choices: List[str]) -> Callable[[str], bool]:
    table = {str(c) for c in choices}
    return lambda v: str(v) in table

class EnumValidator:
    """Callable enum validator with .values()."""
    __slots__ = ("_choices",)
    def __init__(self, choices):
        self._choices = {str(x) for x in choices}
    def __call__(self, v: str) -> bool:
        return str(v) in self._choices
    def values(self) -> List[str]:
        return sorted(self._choices)

__all__ = [
    "validate_param",
    "help_for",
    # primitives to reuse in file modules
    "validate_boolean",
    "validate_integer",
    "validate_nonempty_string",
    "validate_ip",
    "validate_enum",
    "EnumValidator",
]

# ---------------------------
# Module loader
# ---------------------------

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

# ---------------------------
# Name mangling / candidates
# ---------------------------

_SANITIZE = re.compile(r"[^0-9A-Za-z]+")

def _mangle(name: str, lower: bool) -> str:
    s = _SANITIZE.sub("_", str(name))
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "x"
    if s[0].isdigit():
        s = "_" + s
    return s.lower() if lower else s

def _func_candidates(prefix: str, section: str, key: str) -> List[str]:
    # 1) Case-preserving (lets you write validate_CatSleep_Sleep)
    a = f"{prefix}_{_mangle(section, lower=False)}_{_mangle(key, lower=False)}"
    # 2) Lowercase fallback (validate_catsleep_sleep)
    b = f"{prefix}_{_mangle(section, lower=True)}_{_mangle(key, lower=True)}"
    # If a==b, the set will dedupe naturally when iterated.
    return [a, b] if a != b else [a]

# ---------------------------
# Public API
# ---------------------------

def help_for(file_name: str, section: str, key: str) -> Optional[str]:
    """Return a short, user-facing help string for this (file, section, key), or None."""
    mod = _load_module_for(file_name)
    if not mod:
        return None
    for fn_name in _func_candidates("help", section, key):
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            try:
                txt = fn()
                return str(txt) if txt is not None else None
            except Exception:
                return None
    return None

def validate_param(file_name: str, section: str, key: str, value: str) -> Tuple[bool, str]:
    """
    Validate value for (file, section, key).
    Per-file function may return:
        - bool
        - (bool, message)
    When invalid and no custom message, we append the help text if available.
    """
    mod = _load_module_for(file_name)
    if not mod:
        return False, f"No validator module registered for file '{file_name}'."

    for fn_name in _func_candidates("validate", section, key):
        fn = getattr(mod, fn_name, None)
        if callable(fn):
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

            if not msg:
                h = help_for(file_name, section, key)
                msg = f"Invalid value. {h}" if h else "Invalid value."
            return False, msg

    return False, f"No validator for [{section}].{key} in '{file_name}'."
