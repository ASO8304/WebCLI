import configparser
import os

CONFIG_FILE = "/etc/webcli/settings.test"


async def show(websocket, prompt):
    if not os.path.exists(CONFIG_FILE):
        await websocket.send_text("❌ Config file not found.")
        return

    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str  # preserve case sensitivity for keys
    parser.read(CONFIG_FILE)

    sections = parser.sections()
    if not sections:
        await websocket.send_text("⚠️ No sections found.")
        return

    # Step 1: List sections
    await websocket.send_text("📁 Available sections:")
    for i, section in enumerate(sections, 1):
        await websocket.send_text(f"{i}. {section}")
    await websocket.send_text(f"{prompt}Enter number to select section:")

    # Step 2: User selects a section
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

    # Step 3: List keys in section
    await websocket.send_text(f"📂 Keys in [{selected_section}]:")
    for i, key in enumerate(options, 1):
        await websocket.send_text(f"{i}. {key}")
    await websocket.send_text(f"{prompt}Enter number to view key:")

    # Step 4: User selects a key
    while True:
        key_input = await websocket.receive_text()
        if not key_input.isdigit() or not (1 <= int(key_input) <= len(options)):
            await websocket.send_text("❗ Invalid selection. Try again.")
            await websocket.send_text(f"{prompt}Enter number to view key:")
            continue
        break

    selected_key = options[int(key_input) - 1]
    current_value = parser.get(selected_section, selected_key)

    # Step 5: Show key = value
    await websocket.send_text(f"🔎 {selected_key} = {current_value}")
    await websocket.send_text(f"{prompt}Type 'back' or 'edit':")

    # Step 6: Edit or back
    while True:
        action = await websocket.receive_text()
        action = action.strip().lower()

        if action == "back":
            await websocket.send_text("↩️ Returning to config menu.")
            return

        elif action == "edit":
            await websocket.send_text(f"{prompt}Enter new value for {selected_key}:")
            new_value = await websocket.receive_text()

            # No escaping needed — save raw string
            parser.set(selected_section, selected_key, new_value)

            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    parser.write(f)
                await websocket.send_text(f"✅ Updated: {selected_key} = {new_value}")
            except Exception as e:
                await websocket.send_text(f"❌ Failed to write config: {e}")
            return

        else:
            await websocket.send_text("❓ Invalid input. Type 'back' or 'edit':")
            await websocket.send_text(f"{prompt}Type 'back' or 'edit':")
