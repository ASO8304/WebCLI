"""
Per-file validators for: settings.test

Each parameter (per section) exposes two functions:
  - help_<Section>_<Key>() -> str
  - validate_<Section>_<Key>(value: str) -> bool | (bool, str)

Thanks to the router, you can use either CamelCase (as in the INI) or lowercase.
"""

# ------- [CatSleep] -------

def help_CatSleep_Sleep() -> str:
    return "Cat sleep state. Allowed values: yes, trying, no."

def validate_CatSleep_Sleep(value: str):
    allowed = {"yes", "trying", "no"}
    v = str(value).strip().lower()
    return v in allowed


# ------- [clockSleep] -------

def help_clockSleep_Sleep() -> str:
    return "Clock sleep mode. Allowed numeric codes: 0, 2, 43."

def validate_clockSleep_Sleep(value: str):
    allowed = {"0", "2", "43"}
    v = str(value).strip()
    return v in allowed
