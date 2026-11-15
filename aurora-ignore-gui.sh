#!/usr/bin/env bash
#
# Small GUI for the exception list: one Steam AppID per line.
# Saving writes the file the watcher reads, so no service restart is needed.
set -u

FILE="${AURORA_IGNORE_FILE:-$HOME/.config/aurora-ignore.txt}"
TMP="$(mktemp)"
trap 'rm -f "$TMP" "$TMP.new"' EXIT

mkdir -p "$(dirname "$FILE")"
[ -f "$FILE" ] && cp "$FILE" "$TMP"

TEXT="$(zenity --text-info --editable \
    --title="Aurora: Spiele ohne Aurora" \
    --width=460 --height=480 \
    --filename="$TMP" \
    --ok-label="Speichern" --cancel-label="Abbrechen" 2>/dev/null)" || exit 0

printf '%s\n' "$TEXT" \
    | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' \
    | grep -v '^$' \
    | awk '!seen[$0]++' > "$TMP.new"
mv "$TMP.new" "$FILE"

COUNT="$(grep -vcE '^[[:space:]]*#|^[[:space:]]*$' "$FILE" 2>/dev/null || echo 0)"
notify-send -i dialog-information "Aurora-Ausnahmen" "Gespeichert, $COUNT Eintraege in der Liste."
