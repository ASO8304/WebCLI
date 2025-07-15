import configparser
import os

# Directory where config files are stored
CONFIG_DIR = "/etc/webcli"

# Mapping of file names to handler function names (as strings)
CONFIG_MAP = {
    "settings.test": "edit_settings_test",
    "example.ini": "edit_example_ini",           # placeholder
    "custom_config.json": "edit_custom_json"     # placeholder
}

# Main function that lists config files and dispatches to the correct editor
async def show(websocket, prompt):
    if not CONFIG_MAP:
        await websocket.send_text("❌ No config files available.")
        return

    # Show user the available config files
    await websocket.send_text("📄 Available config files:")
    config_files = list(CONFIG_MAP.keys())

    for i, filename in enumerate(config_files, 1):
        await websocket.send_text(f"{i}. {filename}")

    await websocket.send_text(f"{prompt}Enter number to select config file:")

    # Wait for valid file selection
    while True:
        user_input = await websocket.receive_text()
        if not user_input.isdigit() or not (1 <= int(user_input) <= len(config_files)):
            await websocket.send_text("❗ Invalid selection. Try again.")
            continue

        # Determine full path and function name
        selected_file = config_files[int(user_input) - 1]
        full_path = os.path.join(CONFIG_DIR, selected_file)
        handler_name = CONFIG_MAP[selected_file]

        # Dispatch to the function if it exists
        if handler_name in globals():
            handler_func = globals()[handler_name]
            await handler_func(websocket, prompt, full_path)
        else:
            await websocket.send_text(f"⚠️ No handler defined for: {selected_file}")
        return





# Handles INI-style config editing for settings.test
async def edit_settings_test(websocket, prompt, config_path):
    if not os.path.exists(config_path):
        await websocket.send_text(f"❌ Config file not found: {config_path}")
        return

    # Create configparser and preserve key case sensitivity
    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str
    parser.read(config_path)

    sections = parser.sections()
    if not sections:
        await websocket.send_text("⚠️ No sections found.")
        return

    # Step 1: List all sections to user
    await websocket.send_text(f"📁 Sections in {os.path.basename(config_path)}:")
    for i, section in enumerate(sections, 1):
        await websocket.send_text(f"{i}. {section}")
    await websocket.send_text(f"{prompt}Enter number to select section:")

    # Step 2: Let user select a section
    while True:
        section_input = await websocket.receive_text()
        if not section_input.isdigit() or not (1 <= int(section_input) <= len(sections)):
            await websocket.send_text("❗ Invalid selection. Try again.")
            await websocket.send_text(f"{prompt}Enter number to select section:")
            continue
        break

    selected_section = sections[int(section_input) - 1]
    options = parser.options(selected_section)
    if not options:
        await websocket.send_text("⚠️ No keys found in this section.")
        return

    # Step 3: Display all key=value pairs in that section
    await websocket.send_text(f"📂 Keys in [{selected_section}]:")
    for i, key in enumerate(options, 1):
        value = parser.get(selected_section, key)
        await websocket.send_text(f"{i}. {key} = {value}")
    await websocket.send_text(f"{prompt}Type 'edit <number>' to change a value or 'back' to return:")

    # Step 4: Wait for user command ('edit N' or 'back')
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

            # Step 5: Prompt for new value
            selected_key = options[key_index - 1]
            current_value = parser.get(selected_section, selected_key)
            await websocket.send_text(f"🔧 Editing {selected_key} (current = {current_value})")
            await websocket.send_text(f"{prompt}Enter new value for {selected_key}:")

            new_value = await websocket.receive_text()
            parser.set(selected_section, selected_key, new_value)

            # Step 6: Write changes to file
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    parser.write(f)
                await websocket.send_text(f"✅ Updated: {selected_key} = {new_value}")
            except Exception as e:
                await websocket.send_text(f"❌ Failed to write config: {e}")

            return  # After one edit, return to config selection

        else:
            await websocket.send_text("❓ Invalid input. Use 'edit <number>' or 'back':")





# Placeholder for future INI files (can reuse same logic or change)
async def edit_example_ini(websocket, prompt, config_path):
    await websocket.send_text(f"🧪 INI editor not implemented for {config_path}")
    return





# Placeholder for a future JSON config editor
async def edit_custom_json(websocket, prompt, config_path):
    await websocket.send_text(f"📦 JSON editor not implemented for {config_path}")
    return
