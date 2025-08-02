#!/bin/bash

set -e  # Exit on error

# --- Configuration ---
APP_NAME="webcli_server"
USERNAME="webcli"
APP_DIR="/opt/webcli"
CONF_DIR="/etc/webcli"
LOG_DIR="/var/log/webcli"
SERVICE_FILE_NAME="webcli.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_FILE_NAME"
SUDOERS_FILE="/etc/sudoers.d/webcli"

# Nginx-related paths
NGINX_SITE_NAME="cli"
NGINX_CONF_AVAIL="/etc/nginx/sites-available/$NGINX_SITE_NAME"
NGINX_CONF_ENABLED="/etc/nginx/sites-enabled/$NGINX_SITE_NAME"
CLIENT_WEB_DIR="/var/www/cli"

echo "🔧 Starting WebCLI uninstallation..."

# --- Stop and disable the systemd service ---
if systemctl list-units --full -all | grep -q "$SERVICE_FILE_NAME"; then
  echo "🛑 Stopping and disabling systemd service..."
  systemctl stop "$SERVICE_FILE_NAME" || true
  systemctl disable "$SERVICE_FILE_NAME" || true
  systemctl daemon-reload
fi

# --- Remove systemd service file ---
if [ -f "$SERVICE_PATH" ]; then
  echo "🗑 Removing systemd service file..."
  rm -f "$SERVICE_PATH"
  systemctl daemon-reload
fi

# --- Remove application directory ---
if [ -d "$APP_DIR" ]; then
  echo "🗑 Removing application directory: $APP_DIR"
  rm -rf "$APP_DIR"
fi

# --- Remove configuration and log directories ---
if [ -d "$CONF_DIR" ]; then
  echo "🗑 Removing config directory: $CONF_DIR"
  rm -rf "$CONF_DIR"
fi

if [ -d "$LOG_DIR" ]; then
  echo "🗑 Removing log directory: $LOG_DIR"
  rm -rf "$LOG_DIR"
fi

# --- Remove system user ---
if id "$USERNAME" &>/dev/null; then
  echo "👤 Deleting system user: $USERNAME"
  userdel -r "$USERNAME" || true
fi

# --- Remove sudoers entry ---
if [ -f "$SUDOERS_FILE" ]; then
    echo "🧽 Removing sudoers entry..."
    rm -f "$SUDOERS_FILE"
    echo "✅ Removed $SUDOERS_FILE"
else
    echo "ℹ️ No sudoers file found at $SUDOERS_FILE"
fi

# --- Remove Nginx site and reload ---
if [ -f "$NGINX_CONF_ENABLED" ]; then
  echo "🗑 Disabling Nginx site: $NGINX_CONF_ENABLED"
  rm -f "$NGINX_CONF_ENABLED"
fi

if [ -f "$NGINX_CONF_AVAIL" ]; then
  echo "🗑 Removing Nginx site config: $NGINX_CONF_AVAIL"
  rm -f "$NGINX_CONF_AVAIL"
fi

if nginx -t >/dev/null 2>&1; then
  echo "🔁 Reloading Nginx..."
  systemctl reload nginx
else
  echo "⚠️ Nginx config test failed, skipping reload."
fi

# --- Remove static web UI files ---
if [ -d "$CLIENT_WEB_DIR" ]; then
  echo "🗑 Removing static WebCLI files at: $CLIENT_WEB_DIR"
  rm -rf "$CLIENT_WEB_DIR"
fi

echo "✅ Uninstallation complete. WebCLI has been removed from the system."
