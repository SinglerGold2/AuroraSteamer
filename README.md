# aurora-steam-watcher

Starts [Aurora](https://www.cheathappens.com/) automatically inside the Proton
prefix of the running Steam game, so its trainers can attach to the game.

There is a small window for the two settings that matter: the path to
`Aurora.exe` and the list of AppIDs that should **not** start Aurora.

## Why this is needed

Aurora is a Windows program. Proton gives every Steam game its own Wine prefix,
and a process in one prefix cannot see processes in another. Started in its own
prefix, Aurora lists no running game - without any error message.

This tool starts Aurora inside the prefix of the game, with the Wine binary of
the Proton version that runs the game, on every Proton game unless the game is
listed as an exception.

## What you need

1. **Aurora installed**, for example in `~/Aurora/Aurora.exe`. It has to be a
   copy on a Linux filesystem; running it straight from an NTFS drive works in
   many cases but is slower and can fail on file permissions.
2. **Steam with Proton**, and at least one Proton game installed. Native Linux
   games are not affected by this tool.
3. **A desktop with `bash` and `systemd` user services.** The tool does not
   depend on a specific desktop environment.
4. For the window: **Python 3 with GTK 3** (`python-gobject`, package names vary:
   `python-gobject` on Arch, `python3-gi` on Debian/Ubuntu).
5. Optional: **libnotify** for the save confirmation.

## Installation

```bash
git clone https://github.com/SinglerGold2/aurora-steam-watcher.git
cd aurora-steam-watcher
./install.sh
```

The installer copies the script and the window to `~/.local/bin`, installs the
systemd user unit, creates the config and exception files if they are missing,
and enables the service.

## Using the window

Start it from the application menu (**Aurora exceptions**) or with:

```bash
aurora-ignore-gui.py
```

The window has three parts:

- **Path to Aurora.exe** - use *Durchsuchen...* if you are unsure where it is.
- **AppIDs** - one AppID per line, for games that must not start Aurora.
  Blank lines, spaces and duplicates are cleaned up when saving.
- **Hilfe / README** - opens this file.

Saving writes the config, writes the exception list and restarts the watcher, so
changes apply immediately.

The AppID is the number in a game's store URL, for example
`https://store.steampowered.com/app/3321460/`.

## How it works

1. Every `POLL_INTERVAL` seconds the watcher looks for a running Proton game.
2. It reads `STEAM_COMPAT_APP_ID`, `STEAM_COMPAT_DATA_PATH` and
   `STEAM_COMPAT_TOOL_PATHS` from the environment of that process.
3. If the AppID is in the exception list, nothing happens.
4. Otherwise Aurora starts in that prefix, using the game's own Proton.
5. When the game changes, the previous instance is stopped and a new one starts
   in the new prefix.

## Command line

```bash
aurora-steam-watch.sh --dry-run   # print what would happen, start nothing
aurora-steam-watch.sh --once      # one check
aurora-steam-watch.sh             # one check (same as --once)
```

## Configuration file

`~/.config/aurora-steam-watcher.conf`, written by the window. Every setting is
optional and commented in `aurora-steam-watcher.conf.example`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `AURORA_EXE` | `$HOME/Aurora/Aurora.exe` | Path to Aurora.exe |
| `IGNORE_FILE` | `$HOME/.config/aurora-ignore.txt` | Exception list |
| `POLL_INTERVAL` | `10` | Seconds between checks |
| `START_DELAY` | `5` | Seconds to wait before Aurora starts |
| `LOG_FILE` | `$HOME/.local/state/aurora-steam-watch.log` | Log file |
| `STATE_FILE` | `$HOME/.local/state/aurora-steam-watch.state` | Remembers the running instance |

## Troubleshooting

```bash
tail -f ~/.local/state/aurora-steam-watch.log
systemctl --user status aurora-steam-watch.service
```

- *No game detected*: the game must run through Proton, not natively.
- *Aurora starts but lists nothing*: the game may use a different Wine prefix
  than expected; check the log for the detected prefix.
- *Aurora does not start*: check that `AURORA_EXE` exists and that the game's
  Proton directory contains `files/bin/wine`.

## Limitations

- Games with kernel anti-cheat may dislike any injected program. Add their AppID
  to the exception list.
- Aurora is started once per game session and is not stopped when the game exits.
  The next game start reuses or replaces the instance.
- Tested with Aurora 3.5.x, Proton Experimental and GE-Proton on Arch-based
  distributions with KDE Plasma on Wayland.

## License

MIT
