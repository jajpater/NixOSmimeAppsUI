from __future__ import annotations

import re
from pathlib import Path

from .desktop import discover_desktop_entries, mime_index
from .models import DeclarativeState, DesktopEntry, OverrideRule


DEFAULT_REPO_ROOT = Path("/home/jajpater/Develop/nixos-config")
DEFAULT_OUTPUT_RELATIVE = Path("home/modules/generated-mimeapps.nix")


ATTR_RE = re.compile(r'^\s*"(?P<key>[^"]+)"\s*=\s*(?P<value>\[.*\]);\s*$')
OVERRIDE_RE = re.compile(r'^\s*"(?P<key>[^"]+)"\s*=\s*\[\s*(?P<value>.*)\s*\];\s*$')


def _parse_nix_string_list(raw: str) -> list[str]:
    content = raw.strip()
    if not content.startswith("[") or not content.endswith("]"):
      return []
    strings = re.findall(r'"([^"]+)"', content)
    return strings


def load_state(output_path: Path) -> DeclarativeState:
    if not output_path.exists():
      return DeclarativeState()

    state = DeclarativeState()
    current_section: str | None = None

    for line in output_path.read_text(encoding="utf-8").splitlines():
      stripped = line.strip()
      if stripped.startswith("mimeDefaults = {"):
        current_section = "mime_defaults"
        continue
      if stripped.startswith("mimeAdded = {"):
        current_section = "mime_added"
        continue
      if stripped.startswith("mimeRemoved = {"):
        current_section = "mime_removed"
        continue
      if stripped.startswith("desktopOverrides = {"):
        current_section = "desktop_overrides"
        continue
      if stripped == "};":
        current_section = None
        continue

      match = ATTR_RE.match(line)
      if current_section in {"mime_defaults", "mime_added", "mime_removed"} and match:
        key = match.group("key")
        value = _parse_nix_string_list(match.group("value"))
        if current_section == "mime_defaults":
            state.mime_defaults[key] = value
        elif current_section == "mime_added":
            state.mime_added[key] = value
        else:
            state.mime_removed[key] = value
        continue

      match = OVERRIDE_RE.match(line)
      if current_section == "desktop_overrides" and match:
        key = match.group("key")
        value = re.findall(r'"([^"]+)"', match.group("value"))
        state.desktop_overrides[key] = OverrideRule(desktop_id=key, allowed_mime_types=value)

    return state


class MimeRepository:
    def __init__(self, repo_root: Path, output_relative: Path, extra_application_dirs: list[str] | None = None):
        self.repo_root = repo_root
        self.output_path = repo_root / output_relative
        self.entries: dict[str, DesktopEntry] = discover_desktop_entries(extra_application_dirs)
        self.index = mime_index(self.entries)
        self.state = load_state(self.output_path)

    @property
    def mime_types(self) -> list[str]:
        discovered = set(self.index.keys())
        discovered.update(self.state.mime_defaults.keys())
        discovered.update(self.state.mime_added.keys())
        discovered.update(self.state.mime_removed.keys())
        return sorted(discovered)

    def handlers_for(self, mime_type: str) -> list[DesktopEntry]:
        candidate_ids = {entry.desktop_id for entry in self.index.get(mime_type, [])}
        candidate_ids.update(self.state.mime_defaults.get(mime_type, []))
        candidate_ids.update(self.state.mime_added.get(mime_type, []))
        candidate_ids.update(self.state.mime_removed.get(mime_type, []))

        capable_ids = {entry.desktop_id for entry in self.index.get(mime_type, [])}
        explicit_ids = set(candidate_ids)

        entries = list(self.entries.values())
        entries.sort(
            key=lambda entry: (
                0 if entry.desktop_id in explicit_ids else 1,
                0 if entry.desktop_id in capable_ids else 1,
                entry.name.lower(),
                entry.desktop_id,
            )
        )
        return entries

    def current_default_for(self, mime_type: str) -> str | None:
        defaults = self.state.mime_defaults.get(mime_type, [])
        if defaults:
            return defaults[0]
        return None

    def set_default(self, mime_type: str, desktop_id: str) -> None:
        defaults = self.state.mime_defaults.get(mime_type, [])
        new_defaults = [desktop_id] + [item for item in defaults if item != desktop_id]
        self.state.mime_defaults[mime_type] = new_defaults
        added = list(self.state.mime_added.get(mime_type, []))
        if desktop_id not in added:
            added.append(desktop_id)
            added.sort()
            self.state.mime_added[mime_type] = added

    def toggle_added(self, mime_type: str, desktop_id: str) -> bool:
        added = list(self.state.mime_added.get(mime_type, []))
        if desktop_id in added:
            added = [item for item in added if item != desktop_id]
            changed = False
        else:
            added.append(desktop_id)
            added.sort()
            changed = True
        if added:
            self.state.mime_added[mime_type] = added
        else:
            self.state.mime_added.pop(mime_type, None)
        return changed

    def remove_handler(self, mime_type: str, desktop_id: str) -> None:
        added = [item for item in self.state.mime_added.get(mime_type, []) if item != desktop_id]
        if added:
            self.state.mime_added[mime_type] = added
        else:
            self.state.mime_added.pop(mime_type, None)

        defaults = [item for item in self.state.mime_defaults.get(mime_type, []) if item != desktop_id]
        if defaults:
            self.state.mime_defaults[mime_type] = defaults
        else:
            self.state.mime_defaults.pop(mime_type, None)

    def toggle_removed(self, mime_type: str, desktop_id: str) -> bool:
        removed = list(self.state.mime_removed.get(mime_type, []))
        if desktop_id in removed:
            removed = [item for item in removed if item != desktop_id]
            changed = False
        else:
            removed.append(desktop_id)
            removed.sort()
            changed = True
        if removed:
            self.state.mime_removed[mime_type] = removed
        else:
            self.state.mime_removed.pop(mime_type, None)
        return changed

    def toggle_override(self, mime_type: str, desktop_id: str) -> bool:
        entry = self.entries.get(desktop_id)
        if entry is None:
            return False

        current = self.state.desktop_overrides.get(
            desktop_id,
            OverrideRule(desktop_id=desktop_id, allowed_mime_types=list(entry.mime_types)),
        )

        allowed = list(current.allowed_mime_types)
        if mime_type in allowed:
            allowed = [item for item in allowed if item != mime_type]
            enabled = True
        else:
            if mime_type not in entry.mime_types:
                return False
            allowed.append(mime_type)
            allowed.sort()
            enabled = False

        if tuple(allowed) == entry.mime_types:
            self.state.desktop_overrides.pop(desktop_id, None)
        else:
            self.state.desktop_overrides[desktop_id] = OverrideRule(
                desktop_id=desktop_id,
                allowed_mime_types=allowed,
            )
        return enabled

    def is_removed(self, mime_type: str, desktop_id: str) -> bool:
        return desktop_id in self.state.mime_removed.get(mime_type, [])

    def is_added(self, mime_type: str, desktop_id: str) -> bool:
        return desktop_id in self.state.mime_added.get(mime_type, [])

    def supports_mime(self, mime_type: str, desktop_id: str) -> bool:
        entry = self.entries.get(desktop_id)
        if entry is None:
            return False
        return mime_type in entry.mime_types

    def override_for(self, desktop_id: str) -> OverrideRule | None:
        return self.state.desktop_overrides.get(desktop_id)
