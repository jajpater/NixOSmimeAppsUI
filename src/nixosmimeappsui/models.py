from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class DesktopEntry:
    desktop_id: str
    name: str
    exec: str
    icon: str
    generic_name: str
    comment: str
    terminal: bool
    startup_notify: bool
    categories: str
    mime_types: tuple[str, ...]
    source_path: str
    original_text: str


@dataclass
class MimeRule:
    default: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


@dataclass
class OverrideRule:
    desktop_id: str
    allowed_mime_types: list[str] = field(default_factory=list)


@dataclass
class DeclarativeState:
    mime_defaults: dict[str, list[str]] = field(default_factory=dict)
    mime_added: dict[str, list[str]] = field(default_factory=dict)
    mime_removed: dict[str, list[str]] = field(default_factory=dict)
    desktop_overrides: dict[str, OverrideRule] = field(default_factory=dict)
