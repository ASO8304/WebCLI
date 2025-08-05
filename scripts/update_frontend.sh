#!/bin/bash

set -e

# --- Constants ---
CLIENT_SRC_DIR="$(cd "$(dirname "$0")/../client" && pwd)"
CLIENT_DST_DIR="/var/www/cli"

# --- Deploy client files ---
echo "📁 updating static files to $CLIENT_DST_DIR..."
sudo cp "$CLIENT_SRC_DIR"/index.html "$CLIENT_DST_DIR/"
sudo cp "$CLIENT_SRC_DIR"/script.js "$CLIENT_DST_DIR/"
sudo cp "$CLIENT_SRC_DIR"/style.css "$CLIENT_DST_DIR/"
sudo chown -R www-data:www-data "$CLIENT_DST_DIR"
sudo chmod -R 755 "$CLIENT_DST_DIR"


# --- Reload Nginx ---
echo "🔁 Reloading Nginx..."
sudo nginx -t
sudo systemctl reload nginx
