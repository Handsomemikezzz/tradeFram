#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="gui/$(id -u)"
LABELS=(
  "com.waytofree.daily-sync"
  "com.waytofree.midnight-reconcile"
)

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT_DIR/logs"

for LABEL in "${LABELS[@]}"; do
  SOURCE_PLIST="$ROOT_DIR/scripts/$LABEL.plist"
  TARGET_PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
  cp "$SOURCE_PLIST" "$TARGET_PLIST"
  echo "Copied $SOURCE_PLIST -> $TARGET_PLIST"

  launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
  launchctl bootout "$DOMAIN" "$TARGET_PLIST" >/dev/null 2>&1 || true
  if ! launchctl bootstrap "$DOMAIN" "$TARGET_PLIST"; then
    cat >&2 <<EOF
Failed to load $LABEL into $DOMAIN.
The plist was copied, but launchd did not register the timer.
For richer macOS diagnostics, run:
  sudo launchctl bootstrap $DOMAIN "$TARGET_PLIST"
EOF
    exit 1
  fi
  launchctl enable "$DOMAIN/$LABEL"
  launchctl print "$DOMAIN/$LABEL" | sed -n '1,120p'
done
