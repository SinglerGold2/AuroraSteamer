#!/usr/bin/env bash
#
# aurora-steam-watch - starts Aurora inside the Proton prefix of the running
# Steam game, so trainers can attach to the game process.
#
# Why this is needed: Aurora is a Windows program. Proton gives every game its
# own Wine prefix, and a program in one prefix cannot see processes in another.
# Starting Aurora with the same prefix as the game fixes that.
#
# Modes:
#   --once      run one check and exit
#   --loop      check every POLL_INTERVAL seconds (used by the systemd unit)
#   --dry-run   print what would happen, start nothing
set -u

# ---------------------------------------------------------------------------
# Configuration. Every value can be overridden in
# ~/.config/aurora-steam-watcher.conf, which is sourced below if it exists.
# ---------------------------------------------------------------------------

# Path to Aurora.exe
AURORA_EXE="${AURORA_EXE:-$HOME/Aurora/Aurora.exe}"

# File with one Steam AppID per line. Games listed there are skipped.
IGNORE_FILE="${IGNORE_FILE:-$HOME/.config/aurora-ignore.txt}"

# How often the loop looks for a running game, in seconds.
POLL_INTERVAL="${POLL_INTERVAL:-10}"

# Seconds to wait before starting Aurora after the game was detected.
START_DELAY="${START_DELAY:-5}"

# Where to write the log.
LOG_FILE="${LOG_FILE:-$HOME/.local/state/aurora-steam-watch.log}"

# Remembers which game Aurora was started for, as "appid pid".
STATE_FILE="${STATE_FILE:-$HOME/.local/state/aurora-steam-watch.state}"

CONFIG_FILE="${CONFIG_FILE:-$HOME/.config/aurora-steam-watcher.conf}"
[ -f "$CONFIG_FILE" ] && . "$CONFIG_FILE"

# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATE_FILE")"

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_FILE"
}

say() {
    [ "$DRY_RUN" = "1" ] && printf '%s\n' "$*"
    return 0
}

# Prints the PID of the newest running Proton game, or nothing.
find_game_pid() {
    pgrep -f "SteamLaunch AppId=" 2>/dev/null | tail -1
}

# Reads one variable from the environment of a process.
proc_env() {
    local pid="$1" key="$2"
    tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | sed -n "s/^${key}=//p" | head -1
}

# True when the AppID is listed in the ignore file.
is_ignored() {
    local appid="$1"
    [ -f "$IGNORE_FILE" ] || return 1
    grep -qE "^[[:space:]]*${appid}[[:space:]]*$" "$IGNORE_FILE"
}

# Stops the Aurora instance we started, if it is still running.
stop_started_instance() {
    local pid="$1"
    [ -n "$pid" ] || return 0
    kill -0 "$pid" 2>/dev/null && kill "$pid" 2>/dev/null
}

start_aurora() {
    local prefix="$1" wine_bin="$2" appid="$3" pid
    log "starting Aurora for AppID $appid in $prefix"
    WINEPREFIX="$prefix" WINEDEBUG=-all \
        setsid "$wine_bin" "$AURORA_EXE" >/dev/null 2>&1 &
    pid=$!
    printf '%s %s\n' "$appid" "$pid" > "$STATE_FILE"
}

main() {
    local pid appid prefix proton_dir wine_bin
    local previous_appid="" previous_pid=""

    pid="$(find_game_pid)"
    if [ -z "$pid" ]; then
        say "no game running"
        return 0
    fi

    appid="$(proc_env "$pid" STEAM_COMPAT_APP_ID)"
    if [ -z "$appid" ]; then
        log "process $pid has no AppID, skipping"
        return 0
    fi

    if is_ignored "$appid"; then
        say "AppID $appid is ignored"
        return 0
    fi

    prefix="$(proc_env "$pid" STEAM_COMPAT_DATA_PATH)"
    proton_dir="$(proc_env "$pid" STEAM_COMPAT_TOOL_PATHS | cut -d: -f1)"
    if [ -z "$prefix" ] || [ -z "$proton_dir" ]; then
        log "AppID $appid: prefix or Proton directory missing, skipping"
        return 0
    fi

    prefix="$prefix/pfx"
    wine_bin="$proton_dir/files/bin/wine"

    say "AppID $appid"
    say "prefix $prefix"
    say "wine $wine_bin"

    # Reuse a running instance only if it belongs to the same game.
    if [ -f "$STATE_FILE" ]; then
        read -r previous_appid previous_pid < "$STATE_FILE" || true
    fi
    if [ -n "${previous_pid:-}" ] && kill -0 "$previous_pid" 2>/dev/null; then
        if [ "${previous_appid:-}" = "$appid" ]; then
            say "Aurora already running for this game"
            return 0
        fi
        log "game changed from ${previous_appid:-none} to $appid, restarting"
        if [ "$DRY_RUN" = "0" ]; then
            stop_started_instance "$previous_pid"
            sleep 5
        fi
    fi

    if [ ! -x "$wine_bin" ]; then
        log "AppID $appid: wine binary not found at $wine_bin"
        return 0
    fi

    if [ "$DRY_RUN" = "1" ]; then
        return 0
    fi

    sleep "$START_DELAY"
    start_aurora "$prefix" "$wine_bin" "$appid"
}

case "${1:-}" in
    --loop)
        while true; do
            main
            sleep "$POLL_INTERVAL"
        done
        ;;
    *)
        main
        ;;
esac
