# AuroraSteamer 1.2.0

Aurora starts reliably now. Since 1.0.2 three problems were fixed, and the window handling was settled after several attempts.

## What went wrong

```
Native games        The tool path list contains the Steam Linux Runtime first.
                    The launcher took the first entry and never found wine, so
                    Windows games got no Aurora and the log repeated a failure
                    every ten seconds.
Spaces in paths     Proton folders such as "Proton - Experimental" contain
                    spaces. The list was split on whitespace as well as colons,
                    so the path fell apart and no wine was found.
Game stalled        Aurora started five seconds after the Steam launcher, while
                    the Proton prefix was still initialising. Two Wine processes
                    in one prefix stalled the game: Avowed never left its
                    loading screen while Aurora was running.
```

## What changed

```
Native games        recognised and skipped with one log line instead of a loop
Tool paths          split on colons only, so folder names may contain spaces
Warm-up             Aurora starts after GAME_WARMUP seconds (default 45), with a
                    liveness check every five seconds
Window              a normal window manager frame. Aurora paints a full-window
                    interface, so its own top bar sits 40 pixels below the frame
                    and is partly covered. Borderless variants were tried and
                    dropped: they shifted the interface, covered the game frame,
                    or produced no title bar at all.
```

## Installing

Unpack the archive and run `./install.sh`. It installs the script and the window
to `~/.local/bin`, the service `aurorasteamer.service`, the menu entry, icons and
the locales. Configuration goes to `~/.config/aurorasteamer.conf`.

`GAME_WARMUP` and `START_DELAY` can be changed in that file.
