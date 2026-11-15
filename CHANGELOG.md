# Changelog

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
- `install.sh` sets up the watcher, the window, the menu entry, the icons and the
  translations and enables the systemd user service.
