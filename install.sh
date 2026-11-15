#!/usr/bin/env bash
#
# Installs the watcher: script, systemd user unit, ignore file.
set -eu

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config"
UNIT_DIR="$CONFIG_DIR/systemd/user"

mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$UNIT_DIR" "$HOME/.local/state" "$HOME/.local/share/applications" "$HOME/.local/share/doc/aurorasteamer" "$HOME/.local/share/icons/hicolor/scalable/apps"

install -m 755 "$REPO_DIR/aurorasteamer.sh" "$BIN_DIR/aurorasteamer.sh"
install -m 755 "$REPO_DIR/aurorasteamer-gui.py" "$BIN_DIR/aurorasteamer-gui.py"
sed "s|@EXEC@|$BIN_DIR/aurorasteamer-gui.py|" "$REPO_DIR/aurorasteamer.desktop" \
    > "$HOME/.local/share/applications/aurorasteamer.desktop"
chmod 644 "$HOME/.local/share/applications/aurorasteamer.desktop"
install -m 644 "$REPO_DIR/aurorasteamer.service" "$UNIT_DIR/aurorasteamer.service"
install -d "$HOME/.local/share/aurorasteamer/locale"
install -m 644 "$REPO_DIR"/locale/*.json "$HOME/.local/share/aurorasteamer/locale/"

if [ ! -f "$CONFIG_DIR/aurora-ignore.txt" ]; then
    install -m 644 "$REPO_DIR/aurora-ignore.txt.example" "$CONFIG_DIR/aurora-ignore.txt"
    echo "created $CONFIG_DIR/aurora-ignore.txt"
fi

if [ ! -f "$CONFIG_DIR/aurorasteamer.conf" ]; then
    install -m 644 "$REPO_DIR/aurorasteamer.conf.example" "$CONFIG_DIR/aurorasteamer.conf"
    echo "created $CONFIG_DIR/aurorasteamer.conf"
fi

install -m 644 "$REPO_DIR/README.md" "$HOME/.local/share/doc/aurorasteamer/README.md"
install -m 644 "$REPO_DIR/assets/aurorasteamer.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/aurorasteamer.svg"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable --now aurorasteamer.service

echo "installed. check the log with:"
echo "  tail -f $HOME/.local/state/aurorasteamer.log"
