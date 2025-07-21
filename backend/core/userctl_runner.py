import json
import hashlib
import asyncio

FILE_DIR = "/etc/webcli"
USERS_FILE = f"{FILE_DIR}/users.json"
PASS_FILE = f"{FILE_DIR}/pass.json"
VALID_ROLES = ["admin", "operator", "viewer"]

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_passwords():
    with open(PASS_FILE, "r") as f:
        return json.load(f)

def save_passwords(passwords):
    with open(PASS_FILE, "w") as f:
        json.dump(passwords, f, indent=2)

async def cmd_list(websocket, args):
    users = load_users()
    grouped = {}

    for user in users.values():
        role = user['role']
        grouped.setdefault(role, []).append(user['username'])

    msg = "👥 Users grouped by role:\n"
    for role in ["root", "admin", "operator", "viewer"]:
        if role in grouped:
            msg += f"\n🔹 {role.capitalize()}:\n" + "\n".join(f"  - {u}" for u in grouped[role]) + "\n"
    await websocket.send_text(msg)

async def cmd_add(websocket, args):
    if len(args) != 0:
        await websocket.send_text("❌ Usage: userctl add")
        return
    try:
        users = load_users()
        passwords = load_passwords()
        usernames = {user['username'] for user in users.values()}

        while True:
            await websocket.send_text(">>>PROMPT:Enter new username: ")
            username = await websocket.receive_text()
            if username is None:
                await websocket.send_text("❌ Username input failed. Aborting.")
                return
            if username in usernames:
                await websocket.send_text("⚠️ Username already exists. Try again.")
            else:
                break

        await websocket.send_text(">>>PROMPT:Enter password: ")
        password1 = await websocket.receive_text()
        await websocket.send_text(">>>PROMPT:Re-enter password: ")
        password2 = await websocket.receive_text()

        if None in (password1, password2):
            await websocket.send_text("❌ Password input failed. Aborting.")
            return
        if password1 != password2:
            await websocket.send_text("❌ Passwords do not match. Aborting.")
            return

        await websocket.send_text(">>>PROMPT:Enter role (admin/operator/viewer): ")
        while True:
            role = await websocket.receive_text()
            if role is None:
                await websocket.send_text("❌ Role input failed. Aborting.")
                return
            role = role.lower() 
            if role not in VALID_ROLES:
                await websocket.send_text("⚠️ Invalid role. Choose from: admin, operator, viewer.")
                await websocket.send_text(">>>PROMPT:Enter role (admin/operator/viewer): ")
            else:
                break

        new_userid = max(int(u['userid']) for u in users.values()) + 1
        users[username] = {
            "userid": new_userid,
            "username": username,
            "role": role
        }

        save_users(users)
        password_hash = hashlib.sha256(password1.encode()).hexdigest()
        passwords[str(new_userid)] = password_hash
        save_passwords(passwords)

        await websocket.send_text(f"✅ User '{username}' added with role '{role}'.")

    except Exception as e:
        await websocket.send_text(f"❌ Server error: {str(e)}")
        return

async def cmd_delete(websocket, args):
    if len(args) != 1:
        await websocket.send_text("❌ Usage: userctl del <username>")
        return

    username = args[0]
    users = load_users()
    passwords = load_passwords()

    user = users.get(username)
    if not user:
        await websocket.send_text(f"❌ User '{username}' not found.")
        return

    role = user["role"]
    await websocket.send_text(f">>>PROMPT:Are you sure you want to delete user '{username}' with role '{role}'? [y/N]: ")
    confirm = await websocket.receive_text()

    if confirm.strip().lower() != "y":
        await websocket.send_text("❎ Deletion canceled.")
        return

    userid = str(user["userid"])
    users.pop(username)
    passwords.pop(userid, None)

    save_users(users)
    save_passwords(passwords)

    await websocket.send_text(f"🗑️ User '{username}' deleted.")

async def cmd_edit(websocket, args):
    if len(args) != 1:
        await websocket.send_text("❌ Usage: userctl edit <username>")
        return

    username = args[0]
    users = load_users()
    passwords = load_passwords()

    user = users.get(username)
    if not user:
        await websocket.send_text(f"❌ User '{username}' not found.")
        return

    userid = str(user["userid"])
    role = user["role"]
    await websocket.send_text(f"📝 Editing user '{username}' (Role: {role})")
    await websocket.send_text(">>>PROMPT:What do you want to edit?\n1. Password\n2. Role\n3. Cancel\n>>>PROMPT:Enter choice [1/2/3]: ")

    choice = await websocket.receive_text()
    if choice == "1":
        await websocket.send_text(">>>PROMPT:Enter new password: ")
        new_pw1 = await websocket.receive_text()
        await websocket.send_text(">>>PROMPT:Re-enter new password: ")
        new_pw2 = await websocket.receive_text()

        if new_pw1 != new_pw2:
            await websocket.send_text("❌ Passwords do not match. Aborting.")
            return

        password_hash = hashlib.sha256(new_pw1.encode()).hexdigest()
        passwords[userid] = password_hash
        save_passwords(passwords)
        await websocket.send_text(f"🔑 Password for user '{username}' updated.")

    elif choice == "2":
        await websocket.send_text(f">>>PROMPT:Enter new role ({'/'.join(VALID_ROLES)}): ")
        while True:
            new_role = await websocket.receive_text()
            if new_role not in VALID_ROLES:
                await websocket.send_text("⚠️ Invalid role. Try again.")
                await websocket.send_text(f">>>PROMPT:Enter new role ({'/'.join(VALID_ROLES)}): ")
            else:
                break
        user["role"] = new_role
        save_users(users)
        await websocket.send_text(f"👤 Role for user '{username}' updated to '{new_role}'.")

    else:
        await websocket.send_text("❎ Edit canceled.")


# Subcommand dispatcher map with expected arg counts
SUBCOMMANDS = {
    "list": (cmd_list, 0),
    "add": (cmd_add, 0),
    "del": (cmd_delete, 1),
    "edit": (cmd_edit, 1)
}

async def handle_userctl(websocket, full_command: str):
    tokens = full_command.strip().split()
    if len(tokens) < 2:
        await websocket.send_text("❌ Usage: userctl <subcommand> [options]")
        await websocket.send_text("ℹ️ Available subcommands: " + ", ".join(SUBCOMMANDS.keys()))
        return

    subcommand = tokens[1]
    args = tokens[2:]

    handler_info = SUBCOMMANDS.get(subcommand)
    if handler_info is None:
        await websocket.send_text(f"❌ Unknown subcommand '{subcommand}'.")
        await websocket.send_text("ℹ️ Available subcommands: " + ", ".join(SUBCOMMANDS.keys()))
        return

    handler, expected_arg_count = handler_info
    if len(args) != expected_arg_count:
        usage_map = {
            "list": "userctl list",
            "add": "userctl add",
            "del": "userctl del <username>",
            "edit": "userctl edit <username>"
        }
        await websocket.send_text(f"❌ Usage: {usage_map[subcommand]}")
        return

    await handler(websocket, args)



async def autocomplete(tokens):
    subcommands = ["add", "edit", "del", "list"]
    
    if not tokens or len(tokens) == 1:
        return [s for s in subcommands if s.startswith(tokens[0] if tokens else "")]

    sub = tokens[0]
    if sub in ("edit", "del") and len(tokens) == 2:
        users = load_users()
        return [u for u in users if u.startswith(tokens[1])]
    
    return []
