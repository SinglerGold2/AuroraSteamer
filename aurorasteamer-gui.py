#!/usr/bin/env python3
#
# Configuration window for AuroraSteamer.
# It edits the path to Aurora.exe and the AppIDs that must not start Aurora,
# and it offers a language switch between German and English.
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

TEXTS = {
    "de": {
        "title": "AuroraSteamer",
        "subtitle": "Startet Aurora automatisch mit jedem Steam-Spiel.\n"
                    "Spiele, die es nicht sollen, hier eintragen.",
        "language": "Sprache",
        "path": "Pfad zu Aurora.exe",
        "browse": "Durchsuchen...",
        "browse_title": "Aurora.exe auswaehlen",
        "filter": "Windows-Programme (*.exe)",
        "ids": "AppIDs, die NICHT mit Aurora starten sollen (eine pro Zeile):",
        "help": "Hilfe / README",
        "cancel": "Abbrechen",
        "save": "Speichern",
        "saved": "Gespeichert, {count} Eintraege in der Liste.",
        "missing_readme": "Die README wurde nicht gefunden. Bitte das Projekt neu installieren.",
        "open": "Oeffnen",
    },
    "en": {
        "title": "AuroraSteamer",
        "subtitle": "Starts Aurora automatically with every Steam game.\n"
                    "Games that should not be started with it go below.",
        "language": "Language",
        "path": "Path to Aurora.exe",
        "browse": "Browse...",
        "browse_title": "Select Aurora.exe",
        "filter": "Windows programs (*.exe)",
        "ids": "AppIDs that must NOT start Aurora (one per line):",
        "help": "Help / README",
        "cancel": "Cancel",
        "save": "Save",
        "saved": "Saved, {count} entries in the list.",
        "missing_readme": "README not found. Please reinstall the project.",
        "open": "Open",
    },
}


def system_language():
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(variable, "")
        if value.startswith("de"):
            return "de"
        if value.startswith("en"):
            return "en"
    return "en"


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


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title="AuroraSteamer")
        self.language = read_config_value("LANGUAGE", system_language())
        if self.language not in TEXTS:
            self.language = system_language()

        self.set_border_width(12)
        self.set_default_size(660, 580)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(outer)

        # Language row, aligned to the top right corner
        self.language_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.language_row.pack_start(spacer, True, True, 0)

        self.language_label = Gtk.Label()
        self.language_row.pack_start(self.language_label, False, False, 0)

        self.language_combo = Gtk.ComboBoxText()
        self.language_combo.append("de", "Deutsch")
        self.language_combo.append("en", "English")
        self.language_combo.set_active_id(self.language)
        self.language_combo.set_size_request(150, -1)
        self.language_combo.set_popup_fixed_width(False)
        self.language_combo.connect("changed", self.on_language_changed)
        self.language_row.pack_start(self.language_combo, False, False, 0)

        outer.pack_start(self.language_row, False, False, 0)

        # Subtitle
        self.subtitle = Gtk.Label(xalign=0)
        self.subtitle.set_opacity(0.75)
        outer.pack_start(self.subtitle, False, False, 0)

        # Path to Aurora.exe
        self.path_label = Gtk.Label(xalign=0)
        outer.pack_start(self.path_label, False, False, 0)

        exe_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.exe_entry = Gtk.Entry()
        self.exe_entry.set_text(read_config_value("AURORA_EXE", DEFAULT_EXE))
        self.exe_entry.set_hexpand(True)
        exe_row.pack_start(self.exe_entry, True, True, 0)

        self.browse_button = Gtk.Button(width_request=150)
        self.browse_button.connect("clicked", self.on_browse)
        exe_row.pack_start(self.browse_button, False, False, 0)
        outer.pack_start(exe_row, False, False, 0)

        # AppID list
        self.ids_label = Gtk.Label(xalign=0)
        outer.pack_start(self.ids_label, False, False, 0)

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

        self.help_button = Gtk.Button()
        self.help_button.connect("clicked", lambda _button: self.open_readme())
        buttons.pack_start(self.help_button, False, False, 0)

        self.cancel_button = Gtk.Button()
        self.cancel_button.connect("clicked", lambda _button: self.destroy())
        buttons.pack_end(self.cancel_button, False, False, 0)

        self.save_button = Gtk.Button()
        self.save_button.get_style_context().add_class("suggested-action")
        self.save_button.connect("clicked", self.on_save)
        buttons.pack_end(self.save_button, False, False, 0)

        self.apply_language()

    def t(self, key):
        return TEXTS[self.language][key]

    def apply_language(self):
        self.set_title(self.t("title"))
        self.language_label.set_text(self.t("language") + ":")
        self.subtitle.set_text(self.t("subtitle"))
        self.path_label.set_text(self.t("path"))
        self.browse_button.set_label(self.t("browse"))
        self.ids_label.set_text(self.t("ids"))
        self.help_button.set_label(self.t("help"))
        self.cancel_button.set_label(self.t("cancel"))
        self.save_button.set_label(self.t("save"))

    def on_language_changed(self, combo):
        language = combo.get_active_id()
        if language in TEXTS:
            self.language = language
            self.apply_language()

    def on_browse(self, _button):
        dialog = Gtk.FileChooserDialog(
            title=self.t("browse_title"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        file_filter = Gtk.FileFilter()
        file_filter.set_name(self.t("filter"))
        file_filter.add_pattern("*.exe")
        file_filter.add_pattern("*.EXE")
        dialog.add_filter(file_filter)

        if dialog.run() == Gtk.ResponseType.OK:
            self.exe_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def on_save(self, _button):
        buffer = self.text.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        write_config_value("AURORA_EXE", self.exe_entry.get_text().strip())
        write_config_value("LANGUAGE", self.language)
        count = write_ignore(text)
        subprocess.run(["systemctl", "--user", "restart", SERVICE], check=False)
        self.notify(count)
        self.destroy()

    def notify(self, count):
        subprocess.run(
            [
                "notify-send",
                "-i", "aurorasteamer",
                self.t("title"),
                self.t("saved").format(count=count),
            ],
            check=False,
        )

    def open_readme(self):
        path = DOCS
        if not os.path.exists(path):
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
        if os.path.exists(path):
            subprocess.Popen(["xdg-open", path])
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=self.t("missing_readme"),
            )
            dialog.run()
            dialog.destroy()


def main():
    app = Window()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    sys.exit(main())
