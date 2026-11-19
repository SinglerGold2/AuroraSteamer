#!/usr/bin/env bash
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# aurorasteamer - starts Aurora inside the Proton prefix of the running
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
# ~/.config/aurorasteamerer.conf, which is sourced below if it exists.
# ---------------------------------------------------------------------------

# Path to Aurora.exe
AURORA_EXE="${AURORA_EXE:-$HOME/Aurora/Aurora.exe}"

# File with one Steam AppID per line. Games listed there are skipped.
IGNORE_FILE="${IGNORE_FILE:-$HOME/.config/aurora-ignore.txt}"

# How often the loop looks for a running game, in seconds.
POLL_INTERVAL="${POLL_INTERVAL:-10}"

# Slower interval while no game is running. A check costs about 40 ms, so a
# longer idle interval keeps the service close to idle too.
POLL_IDLE_INTERVAL="${POLL_IDLE_INTERVAL:-30}"

# Seconds to wait before starting Aurora after the game was detected.
START_DELAY="${START_DELAY:-5}"

# Remembers which game Aurora was started for, as "appid pid marker". The
# marker is "started" while we believe Aurora runs, and "closed" once it
# disappeared while the game still runs: a person closed it, so it stays
# closed until the game ends. Kept in the runtime directory, so nothing is written to the home
# directory and the file disappears when the session ends.
STATE_FILE="${STATE_FILE:-${XDG_RUNTIME_DIR:-/tmp}/aurorasteamer.state}"

CONFIG_FILE="${CONFIG_FILE:-$HOME/.config/aurorasteamer.conf}"
[ -f "$CONFIG_FILE" ] && . "$CONFIG_FILE"

# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

mkdir -p "$(dirname "$STATE_FILE")"

# Everything goes to stdout, which the systemd unit collects in the journal.
log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

say() {
    [ "$DRY_RUN" = "1" ] && printf '%s\n' "$*"
    return 0
}

# Prints the PID of the newest running Proton game, or nothing.
find_game_pid() {
    pgrep -f "SteamLaunch AppId=" 2>/dev/null | tail -1
}

# Reads one variable from the environment of a process, without spawning helpers.
proc_env() {
    local pid="$1" key="$2" entry
    [ -r "/proc/$pid/environ" ] || return 0
    while IFS= read -r -d '' entry; do
        case "$entry" in
            "${key}="*) printf '%s\n' "${entry#*=}"; return 0;;
        esac
    done < "/proc/$pid/environ"
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
    printf '%s %s started\n' "$appid" "$pid" > "$STATE_FILE"
}

main() {
    local pid appid prefix proton_dir wine_bin
    local previous_appid="" previous_pid="" previous_marker=""

    pid="$(find_game_pid)"
    if [ -z "$pid" ]; then
        # No game: the next one starts with a clean slate, so closing Aurora in
        # one game does not keep it closed in the next.
        [ -f "$STATE_FILE" ] && rm -f "$STATE_FILE"
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

    # The state remembers what happened last time. Read it before anything else
    # is looked up: whether Aurora runs, or was closed, decides the answer on
    # its own.
    if [ -f "$STATE_FILE" ]; then
        read -r previous_appid previous_pid previous_marker < "$STATE_FILE" || true
    fi

    # One instance, ever. If Aurora runs, it is left alone, whatever game is in
    # front: starting a second one would give two windows fighting over the same
    # files.
    if [ -n "${previous_pid:-}" ] && [ "${previous_pid}" != "0" ] && kill -0 "$previous_pid" 2>/dev/null; then
        if [ "${previous_appid:-}" = "$appid" ]; then
            say "Aurora already running for this game"
        else
            say "Aurora already running for AppID ${previous_appid:-unknown}, not starting a second"
        fi
        return 0
    fi

    # It was closed for this very game: leave it closed until the game ends.
    if [ "${previous_appid:-}" = "$appid" ] && [ "${previous_marker:-}" = "closed" ]; then
        say "Aurora was closed for AppID $appid, leaving it closed"
        return 0
    fi

    prefix="$(proc_env "$pid" STEAM_COMPAT_DATA_PATH)"
    proton_dir="$(proc_env "$pid" STEAM_COMPAT_TOOL_PATHS)"
    proton_dir="${proton_dir%%:*}"
    if [ -z "$prefix" ] || [ -z "$proton_dir" ]; then
        log "AppID $appid: prefix or Proton directory missing, skipping"
        return 0
    fi

    prefix="$prefix/pfx"
    wine_bin="$proton_dir/files/bin/wine"

    say "AppID $appid"
    say "prefix $prefix"
    say "wine $wine_bin"

    # One instance, ever. If Aurora runs, it is left alone, whatever game is
    # in front: starting a second one would give two windows fighting over the
    # same files.
    if [ -f "$STATE_FILE" ]; then
        read -r previous_appid previous_pid previous_marker < "$STATE_FILE" || true
    fi
    if [ -n "${previous_pid:-}" ] && [ "${previous_pid}" != "0" ] && kill -0 "$previous_pid" 2>/dev/null; then
        if [ "${previous_appid:-}" = "$appid" ]; then
            say "Aurora already running for this game"
        else
            say "Aurora already running for AppID ${previous_appid:-unknown}, not starting a second"
        fi
        return 0
    fi

    if [ ! -x "$wine_bin" ]; then
        log "AppID $appid: wine binary not found at $wine_bin"
        return 0
    fi

    if [ "${previous_appid:-}" = "$appid" ] && [ -n "${previous_pid:-}" ] && [ "${previous_pid}" != "0" ]; then
        if [ "$DRY_RUN" = "0" ]; then
            printf '%s 0 closed\n' "$appid" > "$STATE_FILE"
        fi
        log "Aurora disappeared while AppID $appid runs, not starting it again"
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
            if [ -n "$(find_game_pid)" ]; then
                sleep "$POLL_INTERVAL"
            else
                sleep "$POLL_IDLE_INTERVAL"
            fi
        done
        ;;
    *)
        main
        ;;
esac
