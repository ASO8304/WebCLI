# core/validators.py

import ipaddress
import re
import json
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import urlparse
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Basic primitives (boolean, int, string, etc.)
# Keep the interface simple: each validator takes a *string* and returns bool.
# ──────────────────────────────────────────────────────────────────────────────

def validate_boolean(value: str) -> bool:
    """
    Accept common boolean forms, case-insensitive:
    true/false, yes/no, 1/0, on/off
    """
    if not isinstance(value, str):
        return False
    return value.strip().lower() in {
        "true", "false", "yes", "no", "1", "0", "on", "off"
    }

def validate_integer(value: str) -> bool:
    """Digits only (leading +/- optional)."""
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"[+-]?\d+", value.strip()))

def validate_float(value: str) -> bool:
    """Accepts ints/floats like 3, -3.2, .5, 1., 1e-3."""
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value.strip()))

def validate_string(value: str) -> bool:
    """Non-empty, non-whitespace string."""
    return isinstance(value, str) and value.strip() != ""

# ──────────────────────────────────────────────────────────────────────────────
# IPs, networks, hostnames, ports, URLs, emails, MACs
# ──────────────────────────────────────────────────────────────────────────────

def validate_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
        return True
    except Exception:
        return False

def validate_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value.strip())
        return True
    except Exception:
        return False

def validate_ipv6(value: str) -> bool:
    try:
        ipaddress.IPv6Address(value.strip())
        return True
    except Exception:
        return False

def validate_cidr(value: str) -> bool:
    """IPv4/IPv6 CIDR (e.g., 192.168.0.0/24, 2001:db8::/32)."""
    try:
        ipaddress.ip_network(value.strip(), strict=False)
        return True
    except Exception:
        return False

def validate_hostname(value: str) -> bool:
    """
    RFC 1123-ish hostname check (labels 1..63 chars, a-z0-9-; no leading/trailing hyphen).
    Overall length <= 253. Trailing dot allowed.
    """
    if not isinstance(value, str):
        return False
    host = value.strip().rstrip(".")
    if not host or len(host) > 253:
        return False
    label_re = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
    return all(label_re.fullmatch(lbl) for lbl in host.split("."))

def validate_url(value: str) -> bool:
    """HTTP/HTTPS URL with a netloc."""
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

def validate_email(value: str) -> bool:
    """Simple email check (not fully RFC-complete, but practical)."""
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value.strip()))

def validate_mac(value: str) -> bool:
    """MAC address 00:11:22:33:44:55 or 00-11-22-33-44-55."""
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"(?:[0-9A-Fa-f]{2}([:-]))(?:[0-9A-Fa-f]{2}\1){4}[0-9A-Fa-f]{2}", value.strip()))

# ──────────────────────────────────────────────────────────────────────────────
# Paths & files
# ──────────────────────────────────────────────────────────────────────────────

def validate_path_any(value: str) -> bool:
    """Crude cross-OS path check: contains / or \\ and not only whitespace."""
    return isinstance(value, str) and value.strip() != "" and ("/" in value or "\\" in value)

def validate_posix_path(value: str) -> bool:
    """POSIX-ish path check (allows relative or absolute)."""
    if not validate_string(value):
        return False
    try:
        PurePosixPath(value)  # will raise if invalid type; not robust but fine for syntax
        return "/" in value or value.startswith(".")
    except Exception:
        return False

def validate_windows_path(value: str) -> bool:
    """
    Windows path check: drive root or UNC, no illegal characters.
    Examples: C:\\Temp\\file.txt, \\\\server\\share\\dir
    """
    if not validate_string(value):
        return False
    if re.match(r"^[A-Za-z]:\\", value) is None and not value.startswith("\\\\"):
        return False
    # Disallow invalid chars <>:"|?*
    return not bool(re.search(r'[<>:"|?*]', value))

def make_file_extension_validator(allowed_exts: set[str]):
    """
    Validate file extension against a set (e.g., {'.json', '.ini'}).
    Case-insensitive.
    """
    allowed = {ext.lower() for ext in allowed_exts}
    def _inner(value: str) -> bool:
        if not validate_string(value):
            return False
        m = re.search(r"(\.[A-Za-z0-9]+)$", value.strip())
        return bool(m) and m.group(1).lower() in allowed
    return _inner

# ──────────────────────────────────────────────────────────────────────────────
# Ranged numbers, percentages, ports, sizes, durations, times
# ──────────────────────────────────────────────────────────────────────────────

def make_int_range_validator(min_val: int | None = None, max_val: int | None = None):
    def _inner(value: str) -> bool:
        if not validate_integer(value):
            return False
        n = int(value)
        if min_val is not None and n < min_val:
            return False
        if max_val is not None and n > max_val:
            return False
        return True
    return _inner

def make_float_range_validator(min_val: float | None = None, max_val: float | None = None):
    def _inner(value: str) -> bool:
        if not validate_float(value):
            return False
        x = float(value)
        if min_val is not None and x < min_val:
            return False
        if max_val is not None and x > max_val:
            return False
        return True
    return _inner

validate_port = make_int_range_validator(1, 65535)
validate_percentage = make_float_range_validator(0.0, 100.0)

def validate_bytes_size(value: str) -> bool:
    """
    Accepts sizes like: 512, 512B, 10KB, 1.5MB, 2GB, 1GiB, 4MiB, etc.
    Units: B, KB, MB, GB, TB, PB (and KiB, MiB, GiB, TiB, PiB).
    """
    if not isinstance(value, str):
        return False
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|PB|KiB|MiB|GiB|TiB|PiB)?\s*", value)
    return bool(m)

def validate_duration(value: str) -> bool:
    """
    Durations like: 30s, 5m, 2h, 1d (no spaces). Optionally allow floats: 1.5h
    """
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"\s*\d+(?:\.\d+)?[smhd]\s*", value))

def validate_time_window(value: str) -> bool:
    """
    Time window HH:MM-HH:MM (24h). Example: 08:30-17:45
    """
    if not isinstance(value, str):
        return False
    m = re.fullmatch(r"\s*(\d{2}):(\d{2})-(\d{2}):(\d{2})\s*", value)
    if not m:
        return False
    h1, m1, h2, m2 = map(int, m.groups())
    if not (0 <= h1 <= 23 and 0 <= m1 <= 59 and 0 <= h2 <= 23 and 0 <= m2 <= 59):
        return False
    start = h1 * 60 + m1
    end = h2 * 60 + m2
    return start < end  # require positive window

def validate_port_range(value: str) -> bool:
    """
    Port range like 1000-2000 (inclusive).
    """
    if not isinstance(value, str):
        return False
    m = re.fullmatch(r"\s*(\d{1,5})-(\d{1,5})\s*", value)
    if not m:
        return False
    a, b = map(int, m.groups())
    return 1 <= a <= 65535 and 1 <= b <= 65535 and a <= b

# ──────────────────────────────────────────────────────────────────────────────
# Data formats (JSON, ISO datetimes), regex, enums, CSV lists, combinators
# ──────────────────────────────────────────────────────────────────────────────

def validate_json(value: str) -> bool:
    try:
        json.loads(value)
        return True
    except Exception:
        return False

def validate_datetime_iso(value: str) -> bool:
    """
    Rough ISO 8601 check: 'YYYY-MM-DD' or full datetime with optional timezone.
    Accepts trailing 'Z' as UTC.
    """
    if not isinstance(value, str):
        return False
    v = value.strip()
    try:
        # datetime only
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        datetime.fromisoformat(v)  # may raise
        return True
    except Exception:
        # try date-only
        try:
            datetime.fromisoformat(v + "T00:00:00")
            return True
        except Exception:
            return False

def make_regex_validator(pattern: str, flags: int = 0):
    rx = re.compile(pattern, flags)
    def _inner(value: str) -> bool:
        return isinstance(value, str) and bool(rx.fullmatch(value.strip()))
    return _inner

def make_enum_validator(choices: set[str] | list[str], case_insensitive: bool = True):
    normalized = {c.lower() if case_insensitive else c for c in choices}
    def _inner(value: str) -> bool:
        if not isinstance(value, str):
            return False
        v = value.strip().lower() if case_insensitive else value.strip()
        return v in normalized
    return _inner

def make_csv_validator(
    item_validator,
    delimiter: str = ",",
    min_len: int | None = None,
    max_len: int | None = None,
    unique: bool = False,
    strip_items: bool = True,
):
    """
    Validate a delimited list (e.g., 'a,b,c'). Each item is validated by item_validator.
    """
    def _inner(value: str) -> bool:
        if not isinstance(value, str):
            return False
        parts = [p.strip() if strip_items else p for p in value.split(delimiter)]
        if min_len is not None and len(parts) < min_len:
            return False
        if max_len is not None and len(parts) > max_len:
            return False
        if unique and len(set(parts)) != len(parts):
            return False
        return all(item_validator(p) for p in parts)
    return _inner

def any_of(*validators):
    """Pass if ANY validator passes."""
    def _inner(value: str) -> bool:
        return any(v(value) for v in validators)
    return _inner

def all_of(*validators):
    """Pass only if ALL validators pass."""
    def _inner(value: str) -> bool:
        return all(v(value) for v in validators)
    return _inner

def negate(validator):
    """Pass if the given validator fails."""
    def _inner(value: str) -> bool:
        return not validator(value)
    return _inner

# ──────────────────────────────────────────────────────────────────────────────
# SAMPLE PARAMETER MAP
# Edit freely. Keep your existing keys if you already rely on them.
# Each key maps to a function(value: str) -> bool.
# ──────────────────────────────────────────────────────────────────────────────

# Example specialized validators you might reuse
validate_hex32 = make_regex_validator(r"[0-9A-Fa-f]{32}")
validate_log_level = make_enum_validator(["debug", "info", "warn", "error"])
validate_tls_mode = make_enum_validator(["off", "optional", "strict"])
validate_file_is_json = make_file_extension_validator({".json"})
validate_username = make_regex_validator(r"[A-Za-z0-9_]{3,32}")

PARAM_VALIDATORS = {
    # ── Your original examples ──
    "IsCatSick": validate_boolean,
    "IsCatHungry": validate_boolean,
    "TVChannelEnable": validate_boolean,
    "ApplyConfigs": validate_boolean,

    "CatHeight": validate_integer,
    "DogHeight": validate_integer,
    "CatAge": validate_integer,
    "DestinationPort": validate_port,

    "ChannelIPAddress": validate_ip,
    "DogAddress": validate_path_any,
    "Name": validate_string,
    "Weather": validate_integer,

    # ── More samples you can adapt ──
    "EnableFeatureX": validate_boolean,
    "LogLevel": validate_log_level,                     # debug|info|warn|error
    "TLSMode": validate_tls_mode,                       # off|optional|strict
    "ListenPort": validate_port,                        # 1..65535
    "PortRange": validate_port_range,                   # e.g., 1000-2000
    "SampleRatePercent": validate_percentage,           # 0..100 (float ok)
    "RetryCount": make_int_range_validator(0, 10),      # integer 0..10
    "Timeout": validate_duration,                       # 30s, 5m, 2h, 1d
    "BufferSize": validate_bytes_size,                  # 10MB, 512KiB, etc.

    "ManagementIPv4": validate_ipv4,
    "ManagementIPv6": validate_ipv6,
    "AllowedCIDRs": make_csv_validator(validate_cidr, min_len=1, unique=True),
    "SyslogServer": any_of(validate_ipv4, validate_hostname),

    "ApiBaseUrl": validate_url,
    "AdminEmail": validate_email,
    "MACWhitelist": make_csv_validator(validate_mac, unique=True),

    "DataDir": validate_posix_path,
    "WindowsShare": validate_windows_path,
    "ConfigFile": validate_file_is_json,                # ends with .json

    "ApiKey": validate_hex32,                           # 32 hex chars
    "Username": validate_username,                      # 3..32 [A-Za-z0-9_]
    "DeviceIDs": make_csv_validator(validate_integer, min_len=1),

    "ActiveHours": validate_time_window,                # e.g., 08:00-17:00
    "StartAt": validate_datetime_iso,                   # ISO 8601-ish
    "ExtraSettingsJSON": validate_json,                 # raw JSON string
}

# ──────────────────────────────────────────────────────────────────────────────
# Optional: a single entry point if you prefer calling one function elsewhere.
# This keeps your current PARAM_VALIDATORS structure but adds a helper.
# ──────────────────────────────────────────────────────────────────────────────

def validate_param(param_name: str, value: str) -> bool:
    """
    Validate a (param_name, value) pair using PARAM_VALIDATORS.
    Returns False if the parameter name is unknown (fail closed).
    """
    validator = PARAM_VALIDATORS.get(param_name)
    if validator is None:
        # Unknown parameter -> reject, or change to True to "allow by default".
        return False
    return validator(value)
