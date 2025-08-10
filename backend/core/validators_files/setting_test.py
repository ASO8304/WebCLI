"""
Per-file validators for: setting.test

Each parameter (per section) exposes two functions:
  - help_<section>_<key>() -> str
  - validate_<section>_<key>(value: str) -> bool | (bool, str)

You can freely edit the help strings below to guide users.
"""

# ------- [CatSleep] -------

def help_catsleep_sleep() -> str:
    return "Cat sleep state. Allowed values: yes, trying, no."

def validate_catsleep_sleep(value: str):
    allowed = {"yes", "trying", "no"}
    v = str(value).strip().lower()
    return v in allowed


# Add more keys for [CatSleep] here if needed
# def help_catsleep_enabled(): return "Enable cat sleep: true or false."
# def validate_catsleep_enabled(value: str): return str(value).lower() in {"true","false"}


# ------- [clockSleep] -------

def help_clocksleep_sleep() -> str:
    return "Clock sleep mode. Allowed numeric codes: 0, 2, 43."

def validate_clocksleep_sleep(value: str):
    allowed = {"0", "2", "43"}
    v = str(value).strip()
    return v in allowed


# Example of a key that wants a custom error message:
# def help_clocksleep_mode(): return "Mode: fast, slow, auto."
# def validate_clocksleep_mode(value: str):
#     if str(value) not in {"fast", "slow", "auto"}:
#         return (False, "Mode must be one of: fast, slow, auto.")  # custom message
#     return True
