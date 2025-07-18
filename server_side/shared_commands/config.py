import configparser
import os
import fnmatch
import re

# Directory where config files are stored
CONFIG_DIR = "/etc/webcli"

# Mapping of config file names to their edit functions
CONFIG_MAP = {
    "settings.test": "edit_ini_format",
    "example.ini": "edit_example_ini",           # Placeholder
    "custom_config.json": "edit_custom_json"     # Placeholder
}


# =======================
# Validation Functions
# =======================

# Validators return True if value is valid, otherwise False
def validate_boolean(value):
    return value.lower() in {"true", "false"}

def validate_integer(value):
    return value.isdigit()

def validate_path(value):
    return "\\" not in value.strip('"')

def validate_ip(value):
    try:
        parts = value.split(".")
        return (
            len(parts) == 4
            and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
        )
    except:
        return False

# Map of patterns to validators
PATTERN_VALIDATORS = [
    ("*Enable", validate_boolean),
    ("IsCat*", validate_boolean),
    ("*Height", validate_integer),
    ("*Age", validate_integer),
    ("*Address", validate_path),
    ("*IPAddress", validate_ip),
    ("*Port", validate_integer),
]

# Look up validator for a given key using fnmatch
def get_validator(key):
    for pattern, validator in PATTERN_VALIDATORS:
        if fnmatch.fnmatch(key, pattern):
            return validator
    return None



# =======================
# Config Menu Dispatcher
# =======================

# Main entrypoint to show config file menu
async def show(websocket, prompt):
    if not CONFIG_MAP:
        await websocket.send_text("❌ No config files available.")
        return

    await websocket.send_text("📄 Available config files:")
    config_files = list(CONFIG_MAP.keys())
    for i, filename in enumerate(config_files, 1):
        await websocket.send_text(f"{i}. {filename}")

    await websocket.send_text(f"{prompt}Enter number to select config file: ")

    while True:
        user_input = await websocket.receive_text()
        if not user_input.isdigit() or not (1 <= int(user_input) <= len(config_files)):
            await websocket.send_text("❗ Invalid selection. Try again.")
            continue

        selected_file = config_files[int(user_input) - 1]
        full_path = os.path.join(CONFIG_DIR, selected_file)
        handler_name = CONFIG_MAP[selected_file]

        if handler_name in globals():
            handler_func = globals()[handler_name]
            await handler_func(websocket, prompt, full_path)
        else:
            await websocket.send_text(f"⚠️ No handler defined for: {selected_file}")
        return



# =======================
# settings.test Editor (INI-style)
# =======================

async def edit_ini_format(websocket, prompt, config_path):
    if not os.path.exists(config_path):
        await websocket.send_text(f"❌ Config file not found: {config_path}")
        return

    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str  # Preserve case
    parser.read(config_path)

    sections = parser.sections()
    if not sections:
        await websocket.send_text("⚠️ No sections found.")
        return

    # Show available sections
    await websocket.send_text(f"📁 Sections in {os.path.basename(config_path)}:")
    for i, section in enumerate(sections, 1):
        await websocket.send_text(f"{i}. {section}")
    await websocket.send_text(f"{prompt}Enter number to select section: ")

    while True:
        section_input = await websocket.receive_text()
        if not section_input.isdigit() or not (1 <= int(section_input) <= len(sections)):
            await websocket.send_text("❗ Invalid selection. Try again.")
            continue
        break

    selected_section = sections[int(section_input) - 1]
    options = parser.options(selected_section)
    if not options:
        await websocket.send_text("⚠️ No keys found in this section.")
        return

    await websocket.send_text(f"📂 Keys in [{selected_section}]:")
    for i, key in enumerate(options, 1):
        value = parser.get(selected_section, key)
        await websocket.send_text(f"{i}. {key} = {value}")
    await websocket.send_text(f"{prompt}Type 'edit <number>' to change a value or 'back' to return: ")

    while True:
        user_input = await websocket.receive_text()
        stripped = user_input.strip().lower()

        if stripped == "back":
            await websocket.send_text("↩️ Returning to config menu.")
            return

        elif stripped.startswith("edit "):
            parts = stripped.split()
            if len(parts) != 2 or not parts[1].isdigit():
                await websocket.send_text("❗ Usage: edit <number>")
                continue

            key_index = int(parts[1])
            if not (1 <= key_index <= len(options)):
                await websocket.send_text("❗ Invalid key number.")
                continue

            selected_key = options[key_index - 1]
            current_value = parser.get(selected_section, selected_key)
            await websocket.send_text(f"🔧 Editing {selected_key} (current = {current_value})")
            await websocket.send_text(f"{prompt}Enter new value for {selected_key}: ")

            new_value = await websocket.receive_text()

            # Validate if a validator exists
            validator = get_validator(selected_key)
            if validator and not validator(new_value):
                await websocket.send_text(f"❌ Invalid value for {selected_key}. Please try again.")
                continue

            parser.set(selected_section, selected_key, new_value)

            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    parser.write(f)
                await websocket.send_text(f"✅ Updated: {selected_key} = {new_value}")
            except Exception as e:
                await websocket.send_text(f"❌ Failed to write config: {e}")

            return  # Return to config file menu after edit

        else:
            await websocket.send_text("❓ Invalid input. Use 'edit <number>' or 'back':")



# =======================
# Future Placeholder Handlers
# =======================

async def edit_example_ini(websocket, prompt, config_path):
    await websocket.send_text(f"🧪 INI editor not implemented for {config_path}")
    return

async def edit_custom_json(websocket, prompt, config_path):
    await websocket.send_text(f"📦 JSON editor not implemented for {config_path}")
    return
