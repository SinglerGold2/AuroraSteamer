# AuroraSteamer 1.0.2

Aurora could not be closed. This release makes closing it final, and it stops the service from ever starting a second window.

## What went wrong

The loop looked for the Aurora process every ten seconds, and a missing process counted as a reason to start one. Closing the window therefore started it again fifteen seconds later, forever, while the game was running. The log showed the same line every fifteen seconds.

## What changed

```
Closing is final     Aurora disappears while its game runs, the service notes
                     that and leaves it closed for that game
One instance, ever   a running Aurora is left alone when another game comes to
                     the front, instead of being killed and restarted
Clean slate          when no game runs, the state is cleared, so the next game
                     starts Aurora as usual
```

The state file now reads `appid pid started|closed`, so the service can tell a running instance from one that was closed on purpose.

## Upgrading

```bash
git pull
./install.sh
systemctl --user restart aurorasteamer.service
```

Nothing has to be removed by hand. The old state file is read as `started` and replaced on the next start.

## Forcing a start

If a game runs and Aurora was closed, it stays closed until that game ends. To start it anyway, delete the state file:

```bash
rm "${XDG_RUNTIME_DIR:-/tmp}/aurorasteamer.state"
```

The service starts it within the next poll, ten seconds later.

## Compatibility

Bash, systemd user units, Steam with Proton. The script reads the game's AppID and prefix from `/proc`, so nothing has to be configured per game. Games can be skipped with `~/.config/aurora-ignore.txt`.

## Thanks

To everyone who reported that the window would not stay closed. The log made it obvious once I read it: fifteen seconds between two starts was the proof.
