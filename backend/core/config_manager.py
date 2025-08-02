import configparser
import os
import fnmatch
import re
from core.validators import *  

# Directory where config files are stored
CONFIG_DIR = "/etc/webcli"

# Mapping of config file names to their edit functions
CONFIG_MAP = {
    "settings.test": "edit_ini_format",
    "example.ini": "edit_example_ini",           # Placeholder
    "custom_config.json": "edit_custom_json"     # Placeholder
}


# Look up validator for a given key using fnmatch
def get_validator(key):
    for param, validator in PARAM_VALIDATORS.items():
        if fnmatch.fnmatch(key, param):
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

    try:
        await websocket.send_text("📄 Available config files:")
        config_files = list(CONFIG_MAP.keys())
        for i, filename in enumerate(config_files, 1):
            await websocket.send_text(f"{i}. {filename}")
    except Exception as e:
        await websocket.send_text(f"❌ Error showing config list: {e}")
        return

    while True:
        try:
            await websocket.send_text(f">>>PROMPT:Enter number to select config file: ")
            user_input = await websocket.receive_text()
        except Exception as e:
            await websocket.send_text(f"❌ Failed to read input: {e}")
            return

        if not user_input.isdigit() or not (1 <= int(user_input) <= len(config_files)):
            await websocket.send_text("❗ Invalid selection. Try again.")
            continue

        try:
            selected_file = config_files[int(user_input) - 1]
            full_path = os.path.join(CONFIG_DIR, selected_file)
            handler_name = CONFIG_MAP[selected_file]

            await websocket.send_text(f"🧠 Loading file: {selected_file}")
            await websocket.send_text(f"🗂 Full path: {full_path}")
            await websocket.send_text(f"🔧 Handler: {handler_name}")

            if handler_name in globals():
                handler_func = globals()[handler_name]
                await handler_func(websocket, prompt, full_path)
            else:
                await websocket.send_text(f"⚠️ No handler defined for: {selected_file}")
            return
        except Exception as e:
            await websocket.send_text(f"❌ Error selecting config file: {e}")
            return



# ========================
# settings.test Editor (INI-style)
# ========================

async def edit_ini_format(websocket, prompt, config_path):
    if not os.path.exists(config_path):
        await websocket.send_text(f"❌ Config file not found: {config_path}")
        return

    parser = configparser.RawConfigParser(strict=False)
    parser.optionxform = str  # preserve case

    try:
        with open(config_path, "r", encoding="utf-8-sig") as f:
            parser.read_file(f)
    except Exception as e:
        await websocket.send_text(f"❌ Failed to parse config: {e}")
        return

    sections = parser.sections()
    if not sections:
        await websocket.send_text("⚠️ No sections found.")
        return

    # Show available sections
    await websocket.send_text(f"📁 Sections in {os.path.basename(config_path)}:")
    for i, section in enumerate(sections, 1):
        await websocket.send_text(f"{i}. {section}")
    await websocket.send_text(f">>>PROMPT:Enter number to select section: ")

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
        try:
            value = parser.get(selected_section, key, fallback="")
            display = value if value else "[empty]"
            await websocket.send_text(f"{i}. {key} = {display}")
        except Exception as e:
            await websocket.send_text(f"❌ Error reading key '{key}': {e}")

    while True:
        await websocket.send_text(f">>>PROMPT:Type 'edit <number>' to change a value or 'back' to return: ")
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
            await websocket.send_text(f">>>PROMPT:Enter new value for {selected_key}: ")

            new_value = await websocket.receive_text()

            # Validate if a validator exists
            validator = get_validator(selected_key)
            if validator and not validator(new_value):
                await websocket.send_text(f"Invalid value for {selected_key}. Please try again.")
                continue
            
            parser.set(selected_section, selected_key, new_value)

            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    parser.write(f)
                await websocket.send_text(f"✅ Updated: {selected_key} = {new_value}")
            except Exception as e:
                await websocket.send_text(f"❌ Failed to write config: {e}")

            return  # Return to config file menu after edit



# =======================
# Future Placeholder Handlers
# =======================

async def edit_example_ini(websocket, prompt, config_path):
    await websocket.send_text(f"🧪 INI editor not implemented for {config_path}")
    return

async def edit_custom_json(websocket, prompt, config_path):
    await websocket.send_text(f"📦 JSON editor not implemented for {config_path}")
    return
