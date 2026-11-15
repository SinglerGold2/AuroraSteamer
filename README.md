# aurora-steam-watcher

Starts [Aurora](https://www.cheathappens.com/) automatically inside the Proton
prefix of the running Steam game, so trainers can attach to the game process.

## Why this is needed

Aurora is a Windows program. Proton gives every Steam game its own Wine prefix,
and a process in one prefix cannot see processes in another. Started in its own
prefix, Aurora simply lists no running game - without any error message.

The fix is to start Aurora inside the prefix of the game, with the Wine binary of
the Proton version that runs the game. This script does exactly that, on every
Proton game, unless the game is listed as an exception.

## How it works

1. Every `POLL_INTERVAL` seconds the script looks for a running Proton game.
2. It reads `STEAM_COMPAT_APP_ID`, `STEAM_COMPAT_DATA_PATH` and
   `STEAM_COMPAT_TOOL_PATHS` from the environment of that process.
3. If the AppID is listed in the ignore file, nothing happens.
4. Otherwise Aurora starts in that prefix, using the game's own Proton.
5. When the game changes, the previous instance is stopped and a new one starts
   in the new prefix.

Native Linux games are not affected: they do not use Proton.

## Installation

```bash
git clone https://github.com/SinglerGold2/aurora-steam-watcher.git
cd aurora-steam-watcher
./install.sh
```

`install.sh` copies the script to `~/.local/bin`, installs the systemd user unit,
creates the ignore file if it does not exist yet and enables the service.

## Configuration

Copy the example and edit it:

```bash
cp aurora-steam-watcher.conf.example ~/.config/aurora-steam-watcher.conf
```

| Setting | Default | Meaning |
| --- | --- | --- |
| `AURORA_EXE` | `$HOME/Aurora/Aurora.exe` | Path to Aurora.exe |
| `IGNORE_FILE` | `$HOME/.config/aurora-ignore.txt` | File with one AppID per line |
| `POLL_INTERVAL` | `10` | Seconds between checks |
| `START_DELAY` | `5` | Seconds to wait before Aurora starts |
| `LOG_FILE` | `$HOME/.local/state/aurora-steam-watch.log` | Log file |
| `STATE_FILE` | `$HOME/.local/state/aurora-steam-watch.state` | Remembers the running instance |

## Exceptions

Add the AppID of a game that must not start Aurora, one per line:

```bash
echo 3321460 >> ~/.config/aurora-ignore.txt
```

The AppID is the number in the game's store URL, for example
`https://store.steampowered.com/app/3321460/`.

The list is read on every check, so a restart is not needed.

## Testing

```bash
aurora-steam-watch.sh --dry-run   # print what would happen, start nothing
tail -f ~/.local/state/aurora-steam-watch.log
```

## Limitations

- Aurora needs a Proton game. Native Linux games are ignored by design.
- Games with kernel anti-cheat may dislike any injected program. Add their AppID
  to the ignore list.
- The script starts Aurora once per game session; it does not stop Aurora when
  the game exits. The next game start reuses or replaces the instance.
- Tested with Aurora 3.5.x, Proton Experimental and GE-Proton on Arch-based
  distributions with KDE Plasma on Wayland.

## License

MIT
