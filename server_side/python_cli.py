#!/usr/bin/env python3

import subprocess
import shutil
import sys
import os
import json
import getpass
import readline
import atexit

# ---------- Persistent command history ----------
histfile = os.path.expanduser("~/.cli_history")
try:
    readline.read_history_file(histfile)
except FileNotFoundError:
    pass
atexit.register(readline.write_history_file, histfile)

# ---------- Policy handling ----------
POLICY_FILE = "policy.json"

def load_policy():
    try:
        with open(POLICY_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load policy file: {e}")
        sys.exit(1)

def is_user_allowed(command, policy):
    user = getpass.getuser()
    allowed_users = policy.get(command, [])
    return "*" in allowed_users or user in allowed_users

# ---------- nmcli interaction ----------
def check_nmcli():
    if shutil.which("nmcli") is None:
        print("Error: 'nmcli' command not found. Please install NetworkManager.")
        sys.exit(1)

def get_ip(interface=None):
    try:
        dev_output = subprocess.check_output(["nmcli", "-t", "-f", "DEVICE", "device", "status"], text=True)
        devices = [line.strip() for line in dev_output.strip().split("\n") if line.strip()]
        found = False
        for dev in devices:
            if interface and dev != interface:
                continue
            try:
                ip_output = subprocess.check_output(["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", dev], text=True)
                ip_lines = [line.strip() for line in ip_output.strip().split("\n") if line.strip()]
                for ip_line in ip_lines:
                    if ip_line.startswith("IP4.ADDRESS"):
                        ip = ip_line.split(":", 1)[1]
                        print(f"{dev}: {ip}")
                        found = True
                        break
            except subprocess.CalledProcessError:
                continue
        if interface and not found:
            print(f"No IP found for interface {interface}")
    except subprocess.CalledProcessError as e:
        print(f"Error listing devices: {e}")

def set_ip(connection_name, ip, gateway):
    try:
        subprocess.run([
            "nmcli", "con", "mod", connection_name,
            "ipv4.method", "manual",
            "ipv4.addresses", ip,
            "ipv4.gateway", gateway,
            "ipv4.dns", "8.8.8.8"
        ], check=True)
        subprocess.run(["nmcli", "con", "down", connection_name], check=True)
        subprocess.run(["nmcli", "con", "up", connection_name], check=True)
        print(f"IP address {ip} set on {connection_name} with gateway {gateway}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to set IP: {e}")

# ---------- CLI ----------
def show_help():
    print("""
Commands:
  get [interface]        Get current IP address (all or specific interface)
  set <conn> <ip/mask> <gw>   Set static IP on a connection name
  help                   Show this help message
  exit / quit            Exit the program
""")

def interactive_cli():
    check_nmcli()
    policy = load_policy()
    print("Network CLI using nmcli (type 'help' for commands)")

    while True:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue
            parts = cmd.split()
            command = parts[0].lower()

            if not is_user_allowed(command, policy):
                print(f"Access denied for user '{getpass.getuser()}' to command '{command}'.")
                continue

            if command in ("exit", "quit"):
                print("Exiting.")
                break
            elif command == "help":
                show_help()
            elif command == "get":
                interface = parts[1] if len(parts) > 1 else None
                get_ip(interface)
            elif command == "set":
                if len(parts) != 4:
                    print("Usage: set <connection_name> <ip/mask> <gateway>")
                else:
                    _, conn, ip, gateway = parts
                    set_ip(conn, ip, gateway)
            else:
                print(f"Unknown command: {command}")
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    interactive_cli()
