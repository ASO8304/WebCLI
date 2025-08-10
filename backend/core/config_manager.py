from configupdater import ConfigUpdater
import os

from core.validators import validate_param, help_for

# Directory where config files are stored
CONFIG_DIR = "/etc/webcli"

# Mapping of config file names to their edit functions
CONFIG_MAP = {
    "settings.test": "edit_ini_format",
    "example.ini": "edit_example_ini",           # Placeholder
    "custom_config.json": "edit_custom_json",    # Placeholder
}

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
                # pass selected_file so validators know which module to use
                await handler_func(websocket, prompt, full_path, selected_file)
            else:
                await websocket.send_text(f"⚠️ No handler defined for: {selected_file}")
            return
        except Exception as e:
            await websocket.send_text(f"❌ Error selecting config file: {e}")
            return

# ========================
# Generic INI Editor
# ========================

async def edit_ini_format(websocket, prompt, config_path, file_name):
    """
    INI editor driven by per-file validators (core/validators_files/<file>.py).
    Shows a short guide as soon as the user types 'edit <n>'.
    """
    if not os.path.exists(config_path):
        await websocket.send_text(f"❌ Config file not found: {config_path}")
        return

    updater = ConfigUpdater()
    updater.optionxform = str  # ✅ preserve case of keys
    try:
        updater.read(config_path, encoding="utf-8-sig")
    except Exception as e:
        await websocket.send_text(f"❌ Failed to parse config: {e}")
        return

    sections = updater.sections()
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

    selected_section_name = sections[int(section_input) - 1]
    selected_section = updater[selected_section_name]

    options = list(selected_section.items())  # [(key, Option)]
    if not options:
        await websocket.send_text("⚠️ No keys found in this section.")
        return

    await websocket.send_text(f"📂 Keys in [{selected_section_name}]:")
    for i, (key, option) in enumerate(options, 1):
        await websocket.send_text(f"{i}. {key} = {option.value}")

    while True:
        await websocket.send_text(
            ">>>PROMPT:Type 'edit <number>' to change a value or 'back' to return: "
        )
        user_input = await websocket.receive_text()
        stripped = user_input.strip().lower()

        if stripped == "back":
            await websocket.send_text("↩️ Returning to config menu.")
            return

        if not stripped.startswith("edit "):
            await websocket.send_text("❗ Usage: edit <number>  |  back")
            continue

        parts = stripped.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await websocket.send_text("❗ Usage: edit <number>")
            continue

        key_index = int(parts[1])
        if not (1 <= key_index <= len(options)):
            await websocket.send_text("❗ Invalid key number.")
            continue

        selected_key, selected_option = options[key_index - 1]

        # 🔹 Show short guide BEFORE prompting for a new value
        guide = help_for(file_name, selected_section_name, selected_key)
        if guide:
            await websocket.send_text(f"ℹ️ {guide}")
        else:
            await websocket.send_text(f"ℹ️ No help available for [{selected_section_name}].{selected_key}.")

        await websocket.send_text(f"🔧 Editing {selected_key} (current = {selected_option.value})")
        await websocket.send_text(f">>>PROMPT:Enter new value for {selected_key}: ")

        new_value = await websocket.receive_text()

        ok, err = validate_param(file_name, selected_section_name, selected_key, new_value)
        if not ok:
            await websocket.send_text(f"❌ {err}")
            # Loop again to let the user retry or choose another key
            continue

        selected_option.value = new_value

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                updater.write(f)
            await websocket.send_text(f"✅ Updated: {selected_key} = {new_value}")
        except Exception as e:
            await websocket.send_text(f"❌ Failed to write config: {e}")
        # After one successful edit, return to config menu
        return

# =======================
# Future Placeholder Handlers
# =======================

async def edit_example_ini(websocket, prompt, config_path, file_name):
    await websocket.send_text(f"🧪 INI editor not implemented for {config_path}")
    return

async def edit_custom_json(websocket, prompt, config_path, file_name):
    await websocket.send_text(f"📦 JSON editor not implemented for {config_path}")
    return
