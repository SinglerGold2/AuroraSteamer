#!/usr/bin/env python3
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Configuration window for AuroraSteamer.
#
# It edits the path to Aurora.exe, manages the exception list of Steam AppIDs
# and resolves the game names for those AppIDs through the Steam store API.
# Game names are cached locally, so a lookup happens only once per AppID.
import json
import os
import subprocess
import sys
import threading
import urllib.parse
import urllib.request

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

try:
    gi.require_version("WebKit2", "4.1")
    from gi.repository import WebKit2  # noqa: E402
except (ValueError, ImportError):
    WebKit2 = None

CONFIG = os.path.expanduser("~/.config/aurorasteamer.conf")
IGNORE = os.path.expanduser("~/.config/aurora-ignore.txt")
CACHE = os.path.expanduser("~/.cache/aurorasteamer/names.json")
DOCS = os.path.expanduser("~/.local/share/doc/aurorasteamer/README.md")
DEFAULT_EXE = os.path.expanduser("~/Aurora/Aurora.exe")
SERVICE = "aurorasteamer.service"

IGNORE_HEADER = (
    "# AppIDs of Steam games that should not start Aurora.\n"
    "# One AppID per line. Lines starting with # are comments.\n"
)




LOCALE_DIRS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale"),
    os.path.expanduser("~/.local/share/aurorasteamer/locale"),
    "/usr/share/aurorasteamer/locale",
]


def locale_dir():
    for folder in LOCALE_DIRS:
        if os.path.isdir(folder):
            return folder
    return None


def load_locales():
    """Reads every *.json from the locale folder: {code: {"name":…, "texts":{…}}}."""
    locales = {}
    folder = locale_dir()
    if not folder:
        return locales
    for entry in sorted(os.listdir(folder)):
        if not entry.endswith(".json"):
            continue
        code = entry[:-len(".json")]
        try:
            with open(os.path.join(folder, entry), encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("texts"), dict):
            data.setdefault("name", code)
            locales[code] = data
    return locales


TEXTS = {}

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
                return os.path.expandvars(line.split("=", 1)[1].strip().strip('"'))
    return default


def write_config_value(key, value):
    lines = []
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as handle:
            lines = handle.read().splitlines()

    new_line = f'{key}="{value}"'
    for index, line in enumerate(lines):
        if line.strip().startswith(key + "="):
            lines[index] = new_line
            break
    else:
        lines.append(new_line)

    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def read_ids():
    if not os.path.exists(IGNORE):
        return []
    ids = []
    with open(IGNORE, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and line.isdigit() and line not in ids:
                ids.append(line)
    return ids


def write_ids(ids):
    lines = IGNORE_HEADER.strip().splitlines() + ids
    os.makedirs(os.path.dirname(IGNORE), exist_ok=True)
    with open(IGNORE, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return len(ids)


def load_cache():
    try:
        with open(CACHE, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=1, sort_keys=True)


STEAM_ROOT = os.path.expanduser("~/.local/share/Steam")
SKIP_APPIDS = {
    "228980",   # Steamworks Common Redistributables
    "1070560",  # Steam Linux Runtime 1.0
    "1391110",  # Steam Linux Runtime 2.0
    "1628350",  # Steam Linux Runtime 3.0
    "4183110",  # Steam Linux Runtime 4.0
    "1493710",  # Proton Experimental
}


def steam_libraries():
    """Returns the Steam library folders that contain a steamapps directory."""
    libraries = []
    main = os.path.join(STEAM_ROOT, "steamapps")
    if os.path.isdir(main):
        libraries.append(os.path.dirname(main))

    vdf = os.path.join(main, "libraryfolders.vdf")
    if os.path.exists(vdf):
        with open(vdf, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if line.startswith('"path"'):
                    parts = line.split('"')
                    if len(parts) >= 4 and os.path.isdir(parts[3]):
                        libraries.append(parts[3])
    return list(dict.fromkeys(libraries))


def installed_games():
    """Returns [(appid, name)] for the games installed in all libraries."""
    games = []
    for library in steam_libraries():
        steamapps = os.path.join(library, "steamapps")
        if not os.path.isdir(steamapps):
            continue
        for entry in sorted(os.listdir(steamapps)):
            if not (entry.startswith("appmanifest_") and entry.endswith(".acf")):
                continue
            appid = entry[len("appmanifest_"):-len(".acf")]
            name = ""
            try:
                with open(os.path.join(steamapps, entry), encoding="utf-8", errors="replace") as handle:
                    for line in handle:
                        line = line.strip()
                        if line.startswith('"name"'):
                            name = line.split('"')[3]
                            break
            except OSError:
                continue
            if not name or appid in SKIP_APPIDS:
                continue
            if "Proton" in name or "Steam Linux Runtime" in name or "Steamworks Common" in name:
                continue
            games.append((appid, name))
    unique = {}
    for appid, name in games:
        unique.setdefault(appid, name)
    return sorted(unique.items(), key=lambda item: item[1].lower())


def fetch_name(appid):
    """Asks the Steam store for the name of an AppID. Returns None on failure."""
    url = (
        "https://store.steampowered.com/api/appdetails?"
        + urllib.parse.urlencode({"appids": appid, "filters": "basic"})
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
    except Exception:
        return None
    entry = data.get(str(appid), {})
    if not entry.get("success"):
        return ""
    return entry.get("data", {}).get("name") or ""


class Row:
    """One exception entry: AppID, resolved game name and a remove button."""

    def __init__(self, window, appid, name=None):
        self.appid = appid
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.id_label = Gtk.Label(label=appid, xalign=0)
        self.id_label.set_width_chars(10)
        self.id_label.set_selectable(True)
        self.name_label = Gtk.Label(xalign=0)
        self.name_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.name_label.set_hexpand(True)
        self.remove_button = Gtk.Button(label=window.t("remove"))
        self.remove_button.set_size_request(110, -1)
        self.remove_button.connect("clicked", window.on_remove_row, self)

        self.box.pack_start(self.id_label, False, False, 0)
        self.box.pack_start(self.name_label, True, True, 0)
        self.box.pack_end(self.remove_button, False, False, 0)
        self.box.show_all()

        self.row = Gtk.ListBoxRow()
        self.row.add(self.box)
        self.window_ref = window
        self.set_name(name)

    def set_name(self, name, failed=False):
        self.name = name
        if name:
            self.name_label.set_text(name)
        elif failed:
            self.name_label.set_text(self.window_ref.t("unknown"))
        else:
            self.name_label.set_text(self.window_ref.t("notfound"))


WATCHER_CSS = b"""
button.watcher-on, button.watcher-on:hover, button.watcher-on:checked {
    background-color: #2e7d32; color: #ffffff; font-weight: bold;
}
button.watcher-off, button.watcher-off:hover, button.watcher-off:checked {
    background-color: #b3261e; color: #ffffff; font-weight: bold;
}
"""


def install_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(WATCHER_CSS)
    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def apply_watcher_style(button, active):
    context = button.get_style_context()
    context.remove_class("watcher-on")
    context.remove_class("watcher-off")
    context.add_class("watcher-on" if active else "watcher-off")


def service_active():
    """True when the watcher service is running."""
    result = subprocess.run(
        ["systemctl", "--user", "is-active", SERVICE],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() == "active"



README_CSS = """
body { background: #1b1b1b; color: #e6e6e6; font-family: sans-serif; margin: 18px; }
h1, h2, h3 { color: #ffffff; margin-top: 18px; }
a { color: #7aa7ff; }
code, pre { background: #262626; color: #e6e6e6; border-radius: 4px; }
code { padding: 1px 4px; }
pre { padding: 10px; }
img { max-width: 100%; }
li { margin: 2px 0; }
"""


def markdown_to_html(text):
    """Small markdown subset: enough for the project README."""
    import html as html_module
    import re

    def inline(value):
        # keep simple raw <img ...> tags from the README, escape the rest
        raw = []

        def keep(match):
            raw.append(match.group(0))
            return f"\x00{len(raw) - 1}\x00"

        value = re.sub(r"<img[^>]*>", keep, value)
        value = html_module.escape(value)
        value = re.sub(r"\x00(\d+)\x00", lambda m: raw[int(m.group(1))], value)
        value = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', value)
        value = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", r'<a href="\2">\1</a>', value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        return value

    out = []
    paragraph = []
    list_kind = None
    in_code = False

    def flush_paragraph():
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append(f"</{list_kind}>")
            list_kind = None

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            out.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            out.append(html_module.escape(line))
            continue

        if not stripped:
            flush_paragraph()
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            flush_paragraph()
            if list_kind != "ul":
                close_list()
                out.append("<ul>")
                list_kind = "ul"
            out.append(f"<li>{inline(bullet.group(1))}")
            continue

        numbered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if numbered:
            flush_paragraph()
            if list_kind != "ol":
                close_list()
                out.append("<ol>")
                list_kind = "ol"
            out.append(f"<li>{inline(numbered.group(1))}")
            continue

        if list_kind and not paragraph:
            # continuation of the current item
            if out and out[-1].startswith("<li>"):
                out[-1] = out[-1] + " " + inline(stripped)
                continue

        if list_kind and out and out[-1].endswith("</li>") is False and out[-1].startswith("<li>"):
            out[-1] = out[-1] + " " + inline(stripped)
            continue

        paragraph.append(stripped)

    flush_paragraph()
    close_list()
    if in_code:
        out.append("</code></pre>")

    # close list items that are still open
    result = []
    for chunk in out:
        if chunk.startswith("<li>") and not chunk.endswith("</li>"):
            chunk += "</li>"
        result.append(chunk)
    return "\n".join(result)


class ConfigDialog(Gtk.Dialog):
    """Edits the two timing values of the watcher."""

    def __init__(self, window):
        super().__init__(title=window.t("config_title"), transient_for=window, flags=0)
        self.window_ref = window
        self.add_button(window.t("cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(window.t("save"), Gtk.ResponseType.OK)
        self.set_default_size(460, 260)

        area = self.get_content_area()
        area.set_spacing(10)
        area.set_border_width(12)

        path_label = Gtk.Label(label=f'{window.t("config_file")}: {CONFIG}', xalign=0)
        path_label.set_selectable(True)
        path_label.set_line_wrap(True)
        area.pack_start(path_label, False, False, 0)

        grid = Gtk.Grid(row_spacing=10, column_spacing=12)
        area.pack_start(grid, False, False, 0)

        poll_label = Gtk.Label(label=window.t("poll_interval"), xalign=0)
        self.poll_spin = Gtk.SpinButton.new_with_range(1, 3600, 1)
        self.poll_spin.set_value(int(read_config_value("POLL_INTERVAL", "10") or 10))
        grid.attach(poll_label, 0, 0, 1, 1)
        grid.attach(self.poll_spin, 1, 0, 1, 1)

        delay_label = Gtk.Label(label=window.t("start_delay"), xalign=0)
        self.delay_spin = Gtk.SpinButton.new_with_range(0, 300, 1)
        self.delay_spin.set_value(int(read_config_value("START_DELAY", "5") or 5))
        grid.attach(delay_label, 0, 1, 1, 1)
        grid.attach(self.delay_spin, 1, 1, 1, 1)

        self.show_all()

    def values(self):
        return int(self.poll_spin.get_value()), int(self.delay_spin.get_value())


class GamesDialog(Gtk.Dialog):
    """Shows the installed Steam games with a checkbox for the exception list."""

    def __init__(self, window, selected):
        super().__init__(title=window.t("games_title"), transient_for=window, flags=0)
        self.window_ref = window
        self.selected = set(selected)
        self.buttons = []

        self.add_button(window.t("cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(window.t("apply"), Gtk.ResponseType.OK)
        self.set_default_size(520, 620)

        area = self.get_content_area()
        area.set_spacing(8)
        area.set_border_width(10)

        hint = Gtk.Label(label=window.t("games_hint"), xalign=0)
        area.pack_start(hint, False, False, 0)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text(window.t("games_search"))
        self.search.connect("search-changed", self.on_search)
        area.pack_start(self.search, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.listbox)
        area.pack_start(scrolled, True, True, 0)

        self.games = installed_games()
        if not self.games:
            empty = Gtk.Label(label=window.t("notfound"), xalign=0)
            self.listbox.add(empty)
        for appid, name in self.games:
            check = Gtk.CheckButton()
            check.set_active(appid in self.selected)
            check.connect("toggled", self.on_toggled, appid)
            label = Gtk.Label(label=f"{name}  ({appid})", xalign=0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.pack_start(check, False, False, 0)
            box.pack_start(label, True, True, 0)
            row = Gtk.ListBoxRow()
            row.add(box)
            row.filter_text = f"{name} {appid}".lower()
            row.show_all()
            self.listbox.add(row)
            self.buttons.append(check)

        self.show_all()

    def on_search(self, entry):
        needle = entry.get_text().lower()
        for row in self.listbox.get_children():
            if hasattr(row, "filter_text"):
                row.set_visible(needle in row.filter_text)

    def on_toggled(self, check, appid):
        if check.get_active():
            self.selected.add(appid)
        else:
            self.selected.discard(appid)


class Window(Gtk.Window):
    def __init__(self):
        super().__init__(title="AuroraSteamer")
        self.locales = load_locales()
        self.language = read_config_value("LANGUAGE", "") or system_language()
        if self.language not in self.locales:
            self.language = system_language() if system_language() in self.locales else next(iter(self.locales), "en")
        self.cache = load_cache()
        self.rows = []
        self.loading = True

        self.set_border_width(12)
        self.set_default_size(680, 620)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(outer)

        # Language row, aligned to the top right corner
        language_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        language_row.pack_start(spacer, True, True, 0)
        self.language_label = Gtk.Label()
        language_row.pack_start(self.language_label, False, False, 0)
        self.language_button = Gtk.MenuButton()
        self.language_button.set_size_request(150, -1)
        self.language_value = Gtk.Label()
        self.language_value.set_ellipsize(Pango.EllipsizeMode.END)
        self.language_value.set_max_width_chars(16)
        self.language_button.add(self.language_value)
        popover = Gtk.Popover()
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        popover_box.set_border_width(4)
        for code, data in sorted(self.locales.items(), key=lambda item: item[1]["name"].lower()):
            button = Gtk.ModelButton(label=data["name"])
            button.connect("clicked", self.on_language_selected, code)
            popover_box.pack_start(button, False, False, 0)
        popover_box.show_all()
        popover.add(popover_box)
        self.language_button.set_popover(popover)
        language_row.pack_start(self.language_button, False, False, 0)
        outer.pack_start(language_row, False, False, 0)

        # Watcher switch
        watcher_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.watcher_button = Gtk.ToggleButton()
        self.watcher_button.set_active(service_active())
        apply_watcher_style(self.watcher_button, self.watcher_button.get_active())
        self.watcher_button.connect("toggled", self.on_watcher_toggled)
        watcher_row.pack_end(self.watcher_button, False, False, 0)
        outer.pack_start(watcher_row, False, False, 0)

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
        ids_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.ids_label = Gtk.Label(xalign=0)
        self.ids_label.set_hexpand(True)
        ids_row.pack_start(self.ids_label, True, True, 0)
        self.games_button = Gtk.Button()
        self.games_button.connect("clicked", self.on_games)
        ids_row.pack_end(self.games_button, False, False, 0)
        outer.pack_start(ids_row, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.listbox)
        outer.pack_start(scrolled, True, True, 0)

        # Add row
        self.add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_entry = Gtk.Entry()
        self.add_entry.set_hexpand(True)
        self.add_entry.set_width_chars(14)
        self.add_entry.connect("activate", self.on_add)
        self.add_box.pack_start(self.add_entry, True, True, 0)
        self.add_button = Gtk.Button()
        self.add_button.connect("clicked", self.on_add)
        self.add_box.pack_start(self.add_button, False, False, 0)
        self.refresh_button = Gtk.Button()
        self.refresh_button.connect("clicked", self.on_refresh)
        self.add_box.pack_start(self.refresh_button, False, False, 0)

        outer.pack_start(self.add_box, False, False, 0)

        # Message line for validation feedback
        self.message = Gtk.Label(xalign=0)
        self.message.set_opacity(0.75)
        outer.pack_start(self.message, False, False, 0)

        # Buttons
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer.pack_start(buttons, False, False, 0)
        self.help_button = Gtk.Button()
        self.help_button.connect("clicked", lambda _button: self.open_readme())
        buttons.pack_start(self.help_button, False, False, 0)
        self.config_button = Gtk.Button()
        self.config_button.connect("clicked", self.on_config)
        buttons.pack_start(self.config_button, False, False, 0)
        self.close_button = Gtk.Button()
        self.close_button.connect("clicked", lambda _button: self.destroy())
        buttons.pack_end(self.close_button, False, False, 0)
        self.save_button = Gtk.Button()
        self.save_button.get_style_context().add_class("suggested-action")
        self.save_button.connect("clicked", self.on_save)
        buttons.pack_end(self.save_button, False, False, 0)

        self.apply_language()
        GLib.idle_add(self.sync_watcher_switch)
        for appid in read_ids():
            self.add_row(appid, self.cache.get(appid))

    def sync_watcher_switch(self):
        """Sets the button once the window is realised, without firing the handler."""
        self.watcher_button.set_active(service_active())
        self.loading = False
        return False

    def t(self, key):
        texts = self.locales.get(self.language, {}).get("texts", {})
        if key in texts:
            return texts[key]
        fallback = self.locales.get("en", {}).get("texts", {})
        return fallback.get(key, key)

    def apply_language(self):
        self.set_title(self.t("title"))
        self.language_label.set_text(self.t("language") + ":")
        self.language_value.set_text(self.locales.get(self.language, {}).get("name", self.language))
        self.set_watcher_button(self.watcher_button.get_active())
        self.subtitle.set_text(self.t("subtitle"))
        self.path_label.set_text(self.t("path"))
        self.browse_button.set_label(self.t("browse"))
        self.ids_label.set_text(self.t("ids"))
        self.add_entry.set_placeholder_text(self.t("add_placeholder"))
        self.add_button.set_label(self.t("add"))
        self.refresh_button.set_label(self.t("refresh"))
        self.games_button.set_label(self.t("games"))
        self.help_button.set_label(self.t("help"))
        self.config_button.set_label(self.t("config"))
        self.close_button.set_label(self.t("close"))
        self.save_button.set_label(self.t("save"))
        for row in self.rows:
            row.remove_button.set_label(self.t("remove"))
            if not row.name:
                row.set_name(None)

    def set_watcher_button(self, active):
        self.watcher_button.set_label(
            self.t("watcher_state_on") if active else self.t("watcher_state_off")
        )
        apply_watcher_style(self.watcher_button, active)

    def on_watcher_toggled(self, button):
        active = button.get_active()
        self.set_watcher_button(active)
        if getattr(self, "loading", False):
            return
        action = "enable" if active else "disable"
        subprocess.run(["systemctl", "--user", action, "--now", SERVICE], check=False)
        self.message.set_text(self.t("watcher_on") if active else self.t("watcher_off"))

    def on_language_selected(self, _button, language):
        if language in self.locales:
            self.language = language
            self.apply_language()
        self.language_button.get_popover().hide()

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

    def add_row(self, appid, name=None):
        row = Row(self, appid, name)
        self.rows.append(row)
        self.listbox.add(row.row)
        self.listbox.show_all()
        if name is None:
            self.resolve_name(row)
        return row

    def resolve_name(self, row):
        row.set_name(self.t("loading"))
        threading.Thread(target=self._resolve_worker, args=(row,), daemon=True).start()

    def _resolve_worker(self, row):
        name = fetch_name(row.appid)
        if name is not None:
            self.cache[row.appid] = name
            save_cache(self.cache)
        GLib.idle_add(self._resolve_done, row, name)

    def _resolve_done(self, row, name):
        if row in self.rows:
            row.set_name(name, failed=name is None)
        return False

    def on_add(self, _widget):
        text = self.add_entry.get_text().strip()
        self.message.set_text("")
        if not text.isdigit():
            self.message.set_text(self.t("invalid"))
            return
        if any(row.appid == text for row in self.rows):
            self.message.set_text(self.t("duplicate"))
            return
        self.add_row(text, self.cache.get(text))
        self.add_entry.set_text("")

    def on_config(self, _button):
        dialog = ConfigDialog(self)
        response = dialog.run()
        poll_interval, start_delay = dialog.values()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        write_config_value("POLL_INTERVAL", poll_interval)
        write_config_value("START_DELAY", start_delay)
        subprocess.run(["systemctl", "--user", "restart", SERVICE], check=False)
        self.message.set_text(f'{self.t("poll_interval")}: {poll_interval}, {self.t("start_delay")}: {start_delay}')

    def on_games(self, _button):
        current = {row.appid for row in self.rows}
        dialog = GamesDialog(self, current)
        response = dialog.run()
        chosen = set(dialog.selected)
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        self.apply_game_selection(chosen, {appid for appid, _name in dialog.games})

    def apply_game_selection(self, chosen, installed_ids):
        """Replaces the installed games in the list, keeps manual entries.

        Entries for games that are no longer installed are kept on purpose: when
        the game comes back, the exception is still there and Aurora stays out of
        it without the user having to think about it again.
        """
        keep = [row.appid for row in self.rows if row.appid not in installed_ids]
        wanted = keep + sorted(set(chosen) - set(keep))
        for row in list(self.rows):
            self.on_remove_row(None, row)
        for appid in wanted:
            self.add_row(appid, self.cache.get(appid))
        self.message.set_text(self.t("saved").format(count=len(wanted)))
        return wanted

    def on_refresh(self, _button):
        self.message.set_text("")
        for row in self.rows:
            if not row.name:
                self.resolve_name(row)

    def on_remove_row(self, _button, row):
        if row in self.rows:
            self.rows.remove(row)
            self.listbox.remove(row.row)

    def on_save(self, _button):
        write_config_value("AURORA_EXE", self.exe_entry.get_text().strip())
        write_config_value("LANGUAGE", self.language)
        count = write_ids([row.appid for row in self.rows])
        subprocess.run(["systemctl", "--user", "restart", SERVICE], check=False)
        message = self.t("saved").format(count=count)
        self.message.set_text(message)
        subprocess.run(
            ["notify-send", "-i", "aurorasteamer", self.t("title"), message],
            check=False,
        )

    def open_readme(self):
        path = DOCS
        if not os.path.exists(path):
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            text = None

        if text is None:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=self.t("missing_readme"),
            )
            dialog.run()
            dialog.destroy()
            return

        dialog = Gtk.Dialog(title="README", transient_for=self, flags=0)
        dialog.add_button(self.t("close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(760, 660)

        area = dialog.get_content_area()
        area.set_border_width(0)

        if WebKit2 is not None:
            view = WebKit2.WebView()
            view.set_background_color(Gdk.RGBA(0.106, 0.106, 0.106, 1.0))
            html_body = markdown_to_html(text)
            html_text = f"<html><head><meta charset='utf-8'><style>{README_CSS}</style></head><body>{html_body}</body></html>"
            base = "file://" + os.path.dirname(os.path.abspath(path)) + "/"
            view.load_html(html_text, base)
            area.pack_start(view, True, True, 0)
        else:
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_vexpand(True)
            view = Gtk.TextView()
            view.set_editable(False)
            view.set_cursor_visible(False)
            view.set_wrap_mode(Gtk.WrapMode.WORD)
            view.get_buffer().set_text(text)
            scrolled.add(view)
            area.pack_start(scrolled, True, True, 0)

        dialog.show_all()
        dialog.run()
        dialog.destroy()


def main():
    install_css()
    app = Window()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    sys.exit(main())
