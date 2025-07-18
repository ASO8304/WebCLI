# validators.py

import ipaddress

# Boolean: true or false (case-insensitive)
def validate_boolean(value):
    return value.lower() in {"true", "false"}

# Integer: only digits
def validate_integer(value):
    return value.isdigit()

# String: basic non-empty string (customize if needed)
def validate_string(value):
    return isinstance(value, str) and value.strip() != ""

# IP Address validation
def validate_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False

# Path: crude check for backslash presence (Windows-style)
def validate_path(value):
    return "\\" in value or "/" in value

# Hardcoded validators mapped by parameter name
PARAM_VALIDATORS = {
    "IsCatSick": validate_boolean,
    "IsCatHungry": validate_boolean,
    "TVChannelEnable": validate_boolean,
    "ApplyConfigs": validate_boolean,
    "CatHeight": validate_integer,
    "DogHeight": validate_integer,
    "CatAge": validate_integer,
    "DestinationPort": validate_integer,
    "ChannelIPAddress": validate_ip,
    "DogAddress": validate_path,
    "Name": validate_string,
    "Weather": validate_string,
}
