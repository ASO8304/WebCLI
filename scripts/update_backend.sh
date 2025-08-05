#!/usr/bin/env bash
# -------------------------------------------------
# update_backend.sh ― selectively refresh /opt/webcli
# -------------------------------------------------
set -euo pipefail

# --- CONFIG ----------------------------------------------------------
SRC_DIR="../backend"        # project’s backend directory
DEST_DIR="/opt/webcli"                 # live backend location
LOG_TAG="webcli-update"                # syslog tag
RSYNC_OPTS="-av --delete --checksum"   # preserves perms, removes obsolete
# ---------------------------------------------------------------------

echo "[$LOG_TAG] Starting backend update…"
logger -t "$LOG_TAG" "Backend update initiated."

# Ensure destination exists
if [[ ! -d "$DEST_DIR" ]]; then
  echo "Destination $DEST_DIR does not exist—creating."
  sudo mkdir -p "$DEST_DIR"
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
echo "[$LOG_TAG] Updating webcli_server.app"
sudo install -m 644 "${SRC_DIR}/webcli_server.py" "${DEST_DIR}/webcli_server.app"

logger -t "$LOG_TAG" "Backend update completed successfully."
echo "[$LOG_TAG] Done."
