#!/bin/bash

set -e

# --- Constants ---
NGINX_CONFIG_PATH="/etc/nginx/sites-available/cli"
NGINX_ENABLED_PATH="/etc/nginx/sites-enabled/cli"
CLIENT_SRC_DIR="$(pwd)"
CLIENT_DST_DIR="/var/www/cli"
CERT_PATH="/etc/ssl/certs/cli.crt"
KEY_PATH="/etc/ssl/private/cli.key"

echo "🔍 Checking for nginx..."
if ! command -v nginx >/dev/null 2>&1; then
    echo "❌ Nginx is not installed."
    echo "💡 Install it using: sudo apt install nginx"
    exit 1
fi

# --- Check TLS certs exist ---
if [[ ! -f "$CERT_PATH" || ! -f "$KEY_PATH" ]]; then
    echo "❌ TLS certificate not found at:"
    echo "   $CERT_PATH"
    echo "   $KEY_PATH"
    echo "💡 Provide valid cert/key or generate one using openssl or certbot"
    exit 1
fi

# --- Deploy client files ---
echo "📁 Copying static files to $CLIENT_DST_DIR..."
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
echo "🔗 Enabling Nginx site..."
sudo ln -sf "$NGINX_CONFIG_PATH" "$NGINX_ENABLED_PATH"

# --- Disable default if present ---
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "🚫 Disabling default site..."
    sudo rm /etc/nginx/sites-enabled/default
fi

# --- Reload Nginx ---
echo "🔁 Reloading Nginx..."
sudo nginx -t
sudo systemctl reload nginx

echo "✅ WebCli is now available at: https://<your-server>/cli/"
