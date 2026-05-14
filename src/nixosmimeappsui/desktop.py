from __future__ import annotations

import configparser
from pathlib import Path

from .models import DesktopEntry


APPLICATION_DIR_CANDIDATES = (
    Path.home() / ".local/share/applications",
    Path("/run/current-system/sw/share/applications"),
    Path("/etc/profiles/per-user") / Path.home().name / "share/applications",
    Path("/nix/var/nix/profiles/default/share/applications"),
)


def _split_mime_types(raw: str) -> tuple[str, ...]:
    return tuple(part for part in raw.split(";") if part)


def parse_desktop_entry(path: Path) -> DesktopEntry | None:
    parser = configparser.RawConfigParser(interpolation=None)
    try:
        original_text = path.read_text(encoding="utf-8")
        parser.read_string(original_text)
    except (OSError, UnicodeDecodeError, configparser.Error):
        return None

    if not parser.has_section("Desktop Entry"):
        return None

    if parser.get("Desktop Entry", "Type", fallback="Application") != "Application":
        return None

    mime_types = _split_mime_types(parser.get("Desktop Entry", "MimeType", fallback=""))
    if not mime_types:
        return None

    desktop_id = path.name
    return DesktopEntry(
        desktop_id=desktop_id,
        name=parser.get("Desktop Entry", "Name", fallback=desktop_id),
        exec=parser.get("Desktop Entry", "Exec", fallback=""),
        icon=parser.get("Desktop Entry", "Icon", fallback=""),
        generic_name=parser.get("Desktop Entry", "GenericName", fallback=""),
        comment=parser.get("Desktop Entry", "Comment", fallback=""),
        terminal=parser.getboolean("Desktop Entry", "Terminal", fallback=False),
        startup_notify=parser.getboolean("Desktop Entry", "StartupNotify", fallback=False),
        categories=parser.get("Desktop Entry", "Categories", fallback=""),
        mime_types=mime_types,
        source_path=str(path),
        original_text=original_text,
    )


def discover_application_dirs(extra_dirs: list[str] | None = None) -> list[Path]:
    candidates = list(APPLICATION_DIR_CANDIDATES)
    if extra_dirs:
        candidates.extend(Path(item) for item in extra_dirs)
    return [path for path in candidates if path.exists()]


def discover_desktop_entries(extra_dirs: list[str] | None = None) -> dict[str, DesktopEntry]:
    entries: dict[str, DesktopEntry] = {}
    for directory in discover_application_dirs(extra_dirs):
        for path in sorted(directory.glob("*.desktop")):
            parsed = parse_desktop_entry(path)
            if parsed is None:
                continue
            entries[parsed.desktop_id] = parsed
    return entries


def mime_index(entries: dict[str, DesktopEntry]) -> dict[str, list[DesktopEntry]]:
    index: dict[str, list[DesktopEntry]] = {}
    for entry in entries.values():
        for mime_type in entry.mime_types:
            index.setdefault(mime_type, []).append(entry)
    for mime_type in index:
        index[mime_type].sort(key=lambda item: (item.name.lower(), item.desktop_id))
    return index
