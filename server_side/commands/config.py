import configparser
import os

CONFIG_FILE = "/etc/webcli/settings.test"


async def show(websocket, prompt):
    if not os.path.exists(CONFIG_FILE):
        await websocket.send_text("❌ Config file not found.")
        return

    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str  # preserve case sensitivity
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

    # Step 2: Select section
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

    # Step 3: Show keys + values
    await websocket.send_text(f"📂 Keys in [{selected_section}]:")
    for i, key in enumerate(options, 1):
        value = parser.get(selected_section, key)
        await websocket.send_text(f"{i}. {key} = {value}")
    await websocket.send_text(f"{prompt}Type 'edit <number>' to change a value or 'back' to return:")

    # Step 4: Command loop
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
            await websocket.send_text(f"{prompt}Enter new value for {selected_key}:")

            new_value = await websocket.receive_text()
            parser.set(selected_section, selected_key, new_value)

            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    parser.write(f)
                await websocket.send_text(f"✅ Updated: {selected_key} = {new_value}")
            except Exception as e:
                await websocket.send_text(f"❌ Failed to write config: {e}")

            return  # Done editing — exit to config menu

        else:
            await websocket.send_text("❓ Invalid input. Use 'edit <number>' or 'back':")
