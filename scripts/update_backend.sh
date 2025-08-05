#!/usr/bin/env bash
# -------------------------------------------------
# update_backend.sh ― refresh /opt/webcli from backend/
# -------------------------------------------------
set -euo pipefail

# --- CONFIG ----------------------------------------------------------
SRC_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/backend"
DEST_DIR="/opt/webcli"                 # live backend location
LOG_TAG="webcli-update"                # syslog tag
RSYNC_OPTS="-av --delete --checksum"   # adjust as needed
# ---------------------------------------------------------------------

echo "[$LOG_TAG] Updating backend…"
logger -t "$LOG_TAG" "Starting backend update from $SRC_DIR to $DEST_DIR"

# Make sure destination exists and is writable
if [[ ! -d "$DEST_DIR" ]]; then
  echo "Destination $DEST_DIR does not exist—creating."
  sudo mkdir -p "$DEST_DIR"
fi

# Backup (optional but smart)
BACKUP="${DEST_DIR}_backup_$(date +%Y%m%d%H%M%S)"
echo "[$LOG_TAG] Creating backup at $BACKUP"
sudo cp -a "$DEST_DIR" "$BACKUP"

# Sync files
echo "[$LOG_TAG] Running rsync…"
sudo rsync $RSYNC_OPTS "$SRC_DIR"/ "$DEST_DIR"/

logger -t "$LOG_TAG" "Backend update completed successfully."
echo "[$LOG_TAG] Done."
