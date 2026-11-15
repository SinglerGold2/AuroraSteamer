#!/usr/bin/env python3
#
# Small configuration window for AuroraSteamer.
# It edits two things: the path to Aurora.exe and the AppIDs that must not
# start Aurora. The README can be opened from the window.
import os
import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

CONFIG = os.path.expanduser("~/.config/aurorasteamer.conf")
IGNORE = os.path.expanduser("~/.config/aurora-ignore.txt")
DOCS = os.path.expanduser("~/.local/share/doc/aurorasteamer/README.md")
DEFAULT_EXE = os.path.expanduser("~/Aurora/Aurora.exe")
SERVICE = "aurorasteamer.service"

IGNORE_HEADER = (
    "# AppIDs of Steam games that should not start Aurora.\n"
    "# One AppID per line. Lines starting with # are comments.\n"
)


def read_config_value(key, default=""):
    if not os.path.exists(CONFIG):
        return default
    with open(CONFIG, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line.startswith(key + "="):
                value = line.split("=", 1)[1].strip().strip('"')
                return os.path.expandvars(value)
    return default


def write_config_value(key, value):
    lines = []
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as handle:
            lines = handle.read().splitlines()

    new_line = f'{key}="{value}"'
    replaced = False
    for index, line in enumerate(lines):
        if line.strip().startswith(key + "="):
            lines[index] = new_line
            replaced = True
            break
    if not replaced:
        lines.append(new_line)

    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def read_ignore():
    if not os.path.exists(IGNORE):
        return ""
    with open(IGNORE, encoding="utf-8") as handle:
        return handle.read()


def write_ignore(text):
    cleaned = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        cleaned.append(line)
    if not cleaned:
        cleaned = IGNORE_HEADER.strip().splitlines()

    os.makedirs(os.path.dirname(IGNORE), exist_ok=True)
    with open(IGNORE, "w", encoding="utf-8") as handle:
        handle.write("\n".join(cleaned) + "\n")
    return len([line for line in cleaned if not line.startswith("#")])


def open_readme():
    path = DOCS
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
    if os.path.exists(path):
        subprocess.Popen(["xdg-open", path])
    else:
        show_error("Die README wurde nicht gefunden. Bitte das Projekt neu installieren.")


def show_error(message):
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=message,
    )
    dialog.run()
    dialog.destroy()


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title="AuroraSteamer")
        self.set_border_width(12)
        self.set_default_size(560, 520)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(outer)

        subtitle = Gtk.Label(
            label="Startet Aurora automatisch mit jedem Steam-Spiel.\n"
                  "Spiele, die es nicht sollen, hier eintragen.",
            xalign=0,
        )
        subtitle.set_opacity(0.75)
        outer.pack_start(subtitle, False, False, 0)

        # Path to Aurora.exe
        exe_label = Gtk.Label(label="Pfad zu Aurora.exe", xalign=0)
        outer.pack_start(exe_label, False, False, 0)

        exe_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.exe_entry = Gtk.Entry()
        self.exe_entry.set_text(read_config_value("AURORA_EXE", DEFAULT_EXE))
        self.exe_entry.set_hexpand(True)
        exe_row.pack_start(self.exe_entry, True, True, 0)

        browse = Gtk.Button(label="Durchsuchen...")
        browse.connect("clicked", self.on_browse)
        exe_row.pack_start(browse, False, False, 0)
        outer.pack_start(exe_row, False, False, 0)

        # AppID list
        ids_label = Gtk.Label(
            label="AppIDs, die NICHT mit Aurora starten sollen (eine pro Zeile):",
            xalign=0,
        )
        outer.pack_start(ids_label, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        self.text = Gtk.TextView()
        self.text.set_monospace(True)
        self.text.get_buffer().set_text(read_ignore())
        scrolled.add(self.text)
        outer.pack_start(scrolled, True, True, 0)

        # Buttons
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer.pack_start(buttons, False, False, 0)

        help_button = Gtk.Button(label="Hilfe / README")
        help_button.connect("clicked", lambda _button: open_readme())
        buttons.pack_start(help_button, False, False, 0)

        cancel = Gtk.Button(label="Abbrechen")
        cancel.connect("clicked", lambda _button: self.destroy())
        buttons.pack_end(cancel, False, False, 0)

        save = Gtk.Button(label="Speichern")
        save.get_style_context().add_class("suggested-action")
        save.connect("clicked", self.on_save)
        buttons.pack_end(save, False, False, 0)

    def on_browse(self, _button):
        dialog = Gtk.FileChooserDialog(
            title="Aurora.exe auswaehlen",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        filter_exe = Gtk.FileFilter()
        filter_exe.set_name("Windows-Programme (*.exe)")
        filter_exe.add_pattern("*.exe")
        filter_exe.add_pattern("*.EXE")
        dialog.add_filter(filter_exe)

        if dialog.run() == Gtk.ResponseType.OK:
            self.exe_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def on_save(self, _button):
        buffer = self.text.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        write_config_value("AURORA_EXE", self.exe_entry.get_text().strip())
        count = write_ignore(text)
        subprocess.run(["systemctl", "--user", "restart", SERVICE], check=False)
        self.notify(count)
        self.destroy()

    def notify(self, count):
        subprocess.run(
            [
                "notify-send",
                "-i", "dialog-information",
                "Aurora Autostart",
                f"Gespeichert, {count} Eintraege in der Liste.",
            ],
            check=False,
        )


def main():
    app = Window()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    sys.exit(main())
