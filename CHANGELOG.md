# Changelog

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
