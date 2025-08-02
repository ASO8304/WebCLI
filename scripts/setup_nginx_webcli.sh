#!/bin/bash

set -e

# Constants
NGINX_CONFIG_PATH="/etc/nginx/sites-available/webcli"
NGINX_ENABLED_PATH="/etc/nginx/sites-enabled/webcli"
CLIENT_SRC_DIR="../client"  # Assumes you're in /client
CLIENT_DST_DIR="/var/www/webcli"

echo "🔍 Checking if nginx is installed..."
if ! command -v nginx >/dev/null 2>&1; then
    echo "❌ Nginx is not installed."
    echo "📦 You can install it using: sudo apt install nginx"
    exit 1
else
    echo "✅ Nginx is installed."
fi

# Create client deployment directory
echo "📁 Creating target directory at $CLIENT_DST_DIR..."
sudo mkdir -p "$CLIENT_DST_DIR"
sudo cp "$CLIENT_SRC_DIR"/index.html "$CLIENT_DST_DIR/"
sudo cp "$CLIENT_SRC_DIR"/script.js "$CLIENT_DST_DIR/"
sudo cp "$CLIENT_SRC_DIR"/style.css "$CLIENT_DST_DIR/"
sudo chown -R www-data:www-data "$CLIENT_DST_DIR"
sudo chmod -R 755 "$CLIENT_DST_DIR"

# Create nginx config
echo "🛠️ Writing Nginx config to $NGINX_CONFIG_PATH..."
sudo tee "$NGINX_CONFIG_PATH" > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location = /webcli {
        return 301 /webcli/;
    }

    location /webcli/ {
        alias $CLIENT_DST_DIR/;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location /webcli/ws {
        proxy_pass http://localhost:12000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF

# Enable site
echo "🔗 Enabling site..."
sudo ln -sf "$NGINX_CONFIG_PATH" "$NGINX_ENABLED_PATH"

# Disable default site if exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "🚫 Disabling default site..."
    sudo rm /etc/nginx/sites-enabled/default
fi

# Test and reload nginx
echo "🔁 Reloading Nginx..."
sudo nginx -t
sudo systemctl reload nginx

echo "✅ WebCLI client is now available at: http://<server-ip>/webcli/"
