#!/usr/bin/env bash
# -------------------------------------------------
# update_backend.sh ― selectively refresh /opt/webcli
# -------------------------------------------------
set -euo pipefail

# --- CONFIG ----------------------------------------------------------
SRC_DIR="../backend"        # project’s backend directory
DEST_DIR="/opt/webcli"      # live backend location
CONFIG_SRC="../config"      # config source directory
CONFIG_DEST="/etc/webcli"  # config destination directory
LOG_TAG="webcli-update"    # syslog tag
RSYNC_OPTS="-av --delete --checksum"   # preserves perms, removes obsolete
# ---------------------------------------------------------------------

echo "[$LOG_TAG] Starting backend update…"
logger -t "$LOG_TAG" "Backend update initiated."

# Ensure destination exists
if [[ ! -d "$DEST_DIR" ]]; then
  echo "Destination $DEST_DIR does not exist—creating."
  sudo mkdir -p "$DEST_DIR"
fi

if [[ ! -d "$CONFIG_DEST" ]]; then
  echo "Config destination $CONFIG_DEST does not exist—creating."
  sudo mkdir -p "$CONFIG_DEST"
fi

# ------- BACKUP (optional but recommended) ---------------------------
BACKUP="${DEST_DIR}_backup_$(date +%Y%m%d%H%M%S)"
echo "[$LOG_TAG] Creating backup at $BACKUP"
sudo cp -a "$DEST_DIR" "$BACKUP"

# ------- SYNC roles/ -------------------------------------------------
echo "[$LOG_TAG] Syncing roles/…"
sudo rsync $RSYNC_OPTS "${SRC_DIR}/roles/" "${DEST_DIR}/roles/"

# ------- SYNC core/ --------------------------------------------------
echo "[$LOG_TAG] Syncing core/…"
sudo rsync $RSYNC_OPTS "${SRC_DIR}/core/" "${DEST_DIR}/core/"

# ------- REPLACE webcli_server --------------------------------------
echo "[$LOG_TAG] Updating webcli_server.py"
sudo install -m 644 "${SRC_DIR}/webcli_server.py" "${DEST_DIR}/webcli_server.py"

# ------- COPY config files -------------------------------------------
echo "[$LOG_TAG] Copying config files (users.json, pass.json) to $CONFIG_DEST"
sudo cp -v "${CONFIG_SRC}/users.json" "${CONFIG_DEST}/users.json"
sudo cp -v "${CONFIG_SRC}/pass.json" "${CONFIG_DEST}/pass.json"

logger -t "$LOG_TAG" "Backend update completed successfully."
echo "[$LOG_TAG] Done."
