# Changelog

## 1.0.7 - 2026-11-24

- Aurora starts inside a Wine virtual desktop (`explorer /desktop=aurora,1600x1200`).
  Aurora draws its own title bar with the trainer's close button, and the window
  manager draws its own decoration on top of it, so the button could not be
  reached. Inside a virtual desktop the window has a normal frame and Aurora's
  own bar stays visible. The desktop host is stopped together with Aurora.

## 1.0.6 - 2026-11-24

- Proton directories with spaces work now, for example "Proton - Experimental".
  The entry list was split on whitespace in addition to colons, so such a path
  fell apart into "Proton", "-" and "Experimental" and no wine was found. The
  service reported "runs without Proton" for Windows games and started no
  Aurora. It splits on colons only now.

## 1.0.5 - 2026-11-22

- Native Linux games are recognised and skipped with one log line. They carry a
  Steam Linux Runtime but no Proton, so there is no wine to start Aurora with.
  Before, the service tried every ten seconds and logged "wine binary not found",
  which looked like a fault.
- Proton is found where it actually is. `STEAM_COMPAT_TOOL_PATHS` lists runtimes
  first and Proton later; the service now takes the entry that has a wine binary
  instead of the first one. This is what kept Crusader Kings III and other games
  from getting Aurora despite running under Proton.

## 1.0.4 - 2026-11-20

- Aurora is stopped when the game it was started for ends. It used to stay as an
  orphan window in the service's cgroup, and a later game found an empty state
  and started a second instance beside it.
- An Aurora that runs without being recorded is adopted instead of duplicated:
  the service takes over its PID and keeps it for the current game.

## 1.0.3 - 2026-11-19

- SteamVR no longer counts as a game. Its own AppID 250820 appears while a VR
  session runs, and the service started Aurora for it on every poll, which looked
  like an Aurora that could not be closed. `IGNORE_APPIDS` now carries steamvr,
  its beta and the Linux runtime.
- The game is found by its environment, not by the newest process whose command
  line matches. Several processes carry `SteamLaunch AppId=`, and only some of
  them have `STEAM_COMPAT_APP_ID`; the old pick failed with "no AppID" every ten
  seconds while SteamVR ran.
- The state stores the PID of the Aurora process, not the launcher's. wine forks
  and exits, so the recorded PID died seconds after the start; the service
  believed Aurora was gone, marked it closed and lost track of a running window.

## 1.0.2 - 2026-11-19

- Aurora can be closed while a game runs. It used to be started again within
  fifteen seconds, which made the window impossible to get rid of. The service
  now notes the close and leaves it closed for that game.
- One instance, ever: a running Aurora is left alone when another game comes to
  the front, instead of being killed and restarted.
- The state file carries a marker (`started`, `closed`), and it is cleared when
  no game runs, so the next game starts Aurora as usual.

## 1.0.1 - 2026-11-16

- The README opens inside the window as rendered HTML; no external editor is
  started any more, and its images are installed next to it.
- The installer also creates PNG icon sizes, for desktops that do not read SVG.
- Runtime state moved to `$XDG_RUNTIME_DIR`, the log goes to the systemd journal;
  the home directory only keeps the config and the exception list.

## 1.0.0 - 2026-11-16

First release.

- Starts Aurora inside the Proton prefix of the running Steam game, so trainers
  can attach to the game process.
- Exception list for games that must not start Aurora, editable in the window or
  picked from the list of installed Steam games.
- Game names for AppIDs are resolved through the Steam store and cached locally.
- Switch to turn the watcher on and off; the state is kept for the next login.
- Settings dialog for the poll interval and the start delay.
- Translations are plain JSON files in `locale/`; German, English and Klingon
  ship with the release.
- Log goes to the systemd journal, runtime state to `$XDG_RUNTIME_DIR`; the home
  directory only gets the config and the exception list.
- `install.sh` sets up the watcher, the window, the menu entry, the icons and the
  translations and enables the systemd user service.
