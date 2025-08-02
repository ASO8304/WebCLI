#!/bin/bash

set -e

# --- Constants ---
NGINX_CONFIG_PATH="/etc/nginx/sites-available/webcli"
NGINX_ENABLED_PATH="/etc/nginx/sites-enabled/webcli"
CLIENT_SRC_DIR="$(cd "$(dirname "$0")/../client" && pwd)"
CLIENT_DST_DIR="/var/www/cli"
CERT_PATH="/etc/ssl/certs/cli.crt"
KEY_PATH="/etc/ssl/private/cli.key"

echo "🔍 Checking for nginx..."
if ! command -v nginx >/dev/null 2>&1; then
    echo "❌ Nginx is not installed."
    echo "💡 Install it using: sudo apt install nginx"
    exit 1
fi

# --- Generate self-signed cert if missing ---
if [[ ! -f "$CERT_PATH" || ! -f "$KEY_PATH" ]]; then
    echo "🔐 TLS certificate not found. Generating self-signed certificate..."
    sudo openssl req -x509 -nodes -days 365 \
      -newkey rsa:2048 \
      -keyout "$KEY_PATH" \
      -out "$CERT_PATH" \
      -subj "/CN=localhost"
    echo "✅ Self-signed TLS certificate created."
else
    echo "✅ TLS certificate already exists."
fi

# --- Deploy frontend files ---
echo "📁 Copying WebCLI client to $CLIENT_DST_DIR..."
sudo mkdir -p "$CLIENT_DST_DIR"
sudo cp "$CLIENT_SRC_DIR"/index.html "$CLIENT_DST_DIR/"
sudo cp "$CLIENT_SRC_DIR"/script.js "$CLIENT_DST_DIR/"
sudo cp "$CLIENT_SRC_DIR"/style.css "$CLIENT_DST_DIR/"
sudo chown -R www-data:www-data "$CLIENT_DST_DIR"
sudo chmod -R 755 "$CLIENT_DST_DIR"

# --- Create Nginx config ---
echo "🛠️ Writing Nginx config to $NGINX_CONFIG_PATH..."
sudo tee "$NGINX_CONFIG_PATH" > /dev/null <<EOF
server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     $CERT_PATH;
    ssl_certificate_key $KEY_PATH;

    location = /cli {
        return 301 /cli/;
    }

    location /cli/ {
        alias $CLIENT_DST_DIR/;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location /cli/ws {
        proxy_pass http://localhost:12000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF

# --- Enable site ---
echo "🔗 Enabling site..."
sudo ln -sf "$NGINX_CONFIG_PATH" "$NGINX_ENABLED_PATH"

# --- Disable default site if it exists ---
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "🚫 Disabling default site..."
    sudo rm /etc/nginx/sites-enabled/default
fi

# --- Reload Nginx ---
echo "🔁 Reloading Nginx..."
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "✅ WebCLI client is now available at:"
echo "   https://<your-server-ip>/cli/"
echo "   (You may need to accept the self-signed cert warning in your browser)"
