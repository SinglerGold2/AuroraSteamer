#!/usr/bin/env bash
#
# Installs the watcher: script, systemd user unit, ignore file.
set -eu

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config"
UNIT_DIR="$CONFIG_DIR/systemd/user"

mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$UNIT_DIR" "$HOME/.local/state" "$HOME/.local/share/applications"

install -m 755 "$REPO_DIR/aurora-steam-watch.sh" "$BIN_DIR/aurora-steam-watch.sh"
install -m 755 "$REPO_DIR/aurora-ignore-gui.sh" "$BIN_DIR/aurora-ignore-gui.sh"
install -m 644 "$REPO_DIR/aurora-ignore-gui.desktop" "$CONFIG_DIR/../.local/share/applications/aurora-ignore-gui.desktop"
install -m 644 "$REPO_DIR/aurora-steam-watch.service" "$UNIT_DIR/aurora-steam-watch.service"

if [ ! -f "$CONFIG_DIR/aurora-ignore.txt" ]; then
    install -m 644 "$REPO_DIR/aurora-ignore.txt.example" "$CONFIG_DIR/aurora-ignore.txt"
    echo "created $CONFIG_DIR/aurora-ignore.txt"
fi

if [ ! -f "$CONFIG_DIR/aurora-steam-watcher.conf" ]; then
    install -m 644 "$REPO_DIR/aurora-steam-watcher.conf.example" "$CONFIG_DIR/aurora-steam-watcher.conf"
    echo "created $CONFIG_DIR/aurora-steam-watcher.conf"
fi

systemctl --user daemon-reload
systemctl --user enable --now aurora-steam-watch.service

echo "installed. check the log with:"
echo "  tail -f $HOME/.local/state/aurora-steam-watch.log"
