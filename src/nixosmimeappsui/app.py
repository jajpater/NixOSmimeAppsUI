from __future__ import annotations

from pathlib import Path

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from .nixgen import render_nix_module, write_nix_module
from .state import DEFAULT_OUTPUT_RELATIVE, DEFAULT_REPO_ROOT, MimeRepository


class ConfirmWriteScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
      yield Vertical(
        Label("Write generated Nix file to disk?"),
        Label("Press y to confirm or n to cancel."),
        id="confirm-dialog",
      )

    def on_key(self, event: events.Key) -> None:
      if event.key == "y":
        self.dismiss(True)
      elif event.key in {"n", "escape"}:
        self.dismiss(False)


class HelpScreen(ModalScreen[None]):
    HELP_TEXT = """NixOSmimeAppsUI Help

This tool writes a delta, not your whole MIME config.

Two layers:
- mimeDefaults / mimeAdded / mimeRemoved
  These are normal XDG associations.
- desktopOverrides
  This changes what an app claims to support in its .desktop file.

Most of the time you only need the first layer.

Keys:
- j / k: move
- h / l: switch pane
- /: search in the focused pane
- a: add selected app as explicit handler
- r: remove selected app from explicit handlers/defaults
- d: set selected app as default
- x: block or unblock selected handler
- o: strip or restore selected MIME claim on the app
- s: refresh preview
- w: write generated Nix file
- q or Esc: close this help
"""

    def compose(self) -> ComposeResult:
      yield Vertical(
        Static(self.HELP_TEXT),
        Static("Press q or Esc to close help."),
        id="help-dialog",
      )

    def on_key(self, event: events.Key) -> None:
      if event.key in {"q", "escape", "question_mark"}:
        self.dismiss()


class MimeApp(ListItem):
    def __init__(self, mime_type: str) -> None:
      super().__init__(Label(mime_type))
      self.mime_type = mime_type


class HandlerItem(ListItem):
    def __init__(self, desktop_id: str, label: str) -> None:
      super().__init__(Label(label))
      self.desktop_id = desktop_id


class NixOSMimeAppsUI(App[None]):
    CSS = """
    Screen {
      layout: vertical;
    }

    #body {
      height: 1fr;
    }

    #left-pane, #right-pane {
      width: 1fr;
      height: 1fr;
      border: solid $panel;
    }

    #preview-pane {
      width: 2fr;
      border: solid $panel;
    }

    #mime-search {
      dock: top;
    }

    #status {
      height: 3;
      border-top: solid $panel;
      padding: 0 1;
    }

    #confirm-dialog {
      width: 60;
      height: 6;
      border: round $accent;
      background: $surface;
      padding: 1 2;
      align: center middle;
    }

    #help-dialog {
      width: 90;
      height: 22;
      border: round $accent;
      background: $surface;
      padding: 1 2;
      align: center middle;
    }
    """

    BINDINGS = [
      Binding("q", "quit", "Quit"),
      Binding("question_mark", "show_help", "Help"),
      Binding("j", "cursor_down", "Down", show=False),
      Binding("k", "cursor_up", "Up", show=False),
      Binding("h", "focus_left", "Left", show=False),
      Binding("l", "focus_right", "Right", show=False),
      Binding("/", "focus_search", "Search"),
      Binding("a", "toggle_added", "Toggle Added"),
      Binding("r", "remove_handler", "Remove Handler"),
      Binding("d", "set_default", "Set Default"),
      Binding("x", "toggle_removed", "Toggle Block"),
      Binding("o", "toggle_override", "Toggle Override"),
      Binding("s", "refresh_preview", "Preview"),
      Binding("w", "write_file", "Write"),
    ]

    filtered_mime_types: reactive[list[str]] = reactive(list)
    filtered_handler_ids: reactive[list[str] | None] = reactive(None)

    def __init__(self, repo_root: Path | None = None, output_relative: Path | None = None):
      super().__init__()
      self.repository = MimeRepository(
        repo_root=repo_root or DEFAULT_REPO_ROOT,
        output_relative=output_relative or DEFAULT_OUTPUT_RELATIVE,
      )
      self.filtered_mime_types = self.repository.mime_types
      self.search_target = "mime"
      self.preview_text = ""

    def compose(self) -> ComposeResult:
      yield Header()
      yield Input(placeholder="Search current pane", id="pane-search")
      with Horizontal(id="body"):
        with Vertical(id="left-pane"):
          yield Label("MIME Types")
          yield ListView(id="mime-list")
        with Vertical(id="right-pane"):
          yield Label("Handlers")
          yield ListView(id="handler-list")
        with Vertical(id="preview-pane"):
          yield Label("Generated Nix Preview")
          yield Static("", id="preview")
      yield Static("", id="status")
      yield Footer()

    def on_mount(self) -> None:
      self._reload_mime_list()
      self._refresh_preview()
      self.query_one("#pane-search", Input).blur()
      self.query_one("#mime-list", ListView).focus()

    def _set_status(self, message: str) -> None:
      self.query_one("#status", Static).update(message)

    def _reload_mime_list(self) -> None:
      mime_list = self.query_one("#mime-list", ListView)
      mime_list.clear()
      for mime_type in self.filtered_mime_types:
        mime_list.append(MimeApp(mime_type))
      if self.filtered_mime_types:
        mime_list.index = 0
        self._reload_handler_list(self.filtered_mime_types[0])

    def _current_mime_type(self) -> str | None:
      mime_list = self.query_one("#mime-list", ListView)
      item = mime_list.highlighted_child
      if isinstance(item, MimeApp):
        return item.mime_type
      return None

    def _current_handler_id(self) -> str | None:
      handler_list = self.query_one("#handler-list", ListView)
      item = handler_list.highlighted_child
      if isinstance(item, HandlerItem):
        return item.desktop_id
      return None

    def _handler_label(self, mime_type: str, desktop_id: str) -> str:
      entry = self.repository.entries[desktop_id]
      flags: list[str] = []
      if self.repository.supports_mime(mime_type, desktop_id):
        flags.append("supports")
      if self.repository.is_added(mime_type, desktop_id):
        flags.append("added")
      if self.repository.current_default_for(mime_type) == desktop_id:
        flags.append("default")
      if self.repository.is_removed(mime_type, desktop_id):
        flags.append("blocked")
      override = self.repository.override_for(desktop_id)
      if override is not None and mime_type not in override.allowed_mime_types:
        flags.append("stripped")
      if not self.repository.supports_mime(mime_type, desktop_id) and not self.repository.is_added(mime_type, desktop_id):
        flags.append("not-advertised")
      suffix = f" [{' | '.join(flags)}]" if flags else ""
      return f"{entry.name} ({desktop_id}){suffix}"

    def _reload_handler_list(self, mime_type: str) -> None:
      handler_list = self.query_one("#handler-list", ListView)
      handler_list.clear()
      entries = self.repository.handlers_for(mime_type)
      if self.filtered_handler_ids is not None:
        allowed_ids = set(self.filtered_handler_ids)
        entries = [entry for entry in entries if entry.desktop_id in allowed_ids]
      for entry in entries:
        handler_list.append(HandlerItem(entry.desktop_id, self._handler_label(mime_type, entry.desktop_id)))
      if entries:
        handler_list.index = 0

    def _refresh_preview(self) -> None:
      self.preview_text = render_nix_module(self.repository.state, self.repository.entries)
      self.query_one("#preview", Static).update(self.preview_text)
      self._set_status(f"Preview refreshed for {self.repository.output_path}")

    def on_input_changed(self, event: Input.Changed) -> None:
      query = event.value.strip().lower()
      if self.search_target == "mime":
        self.filtered_handler_ids = None
        if not query:
          self.filtered_mime_types = self.repository.mime_types
        else:
          self.filtered_mime_types = [
            mime_type for mime_type in self.repository.mime_types
            if query in mime_type.lower()
          ]
        self._reload_mime_list()
      else:
        mime_type = self._current_mime_type()
        if mime_type is None:
          return
        entries = self.repository.handlers_for(mime_type)
        if not query:
          self.filtered_handler_ids = None
        else:
          self.filtered_handler_ids = [
            entry.desktop_id for entry in entries
            if query in entry.desktop_id.lower() or query in entry.name.lower()
          ]
        self._reload_handler_list(mime_type)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
      if event.list_view.id == "mime-list":
        mime_type = self._current_mime_type()
        if mime_type is not None:
          self._reload_handler_list(mime_type)

    def action_cursor_down(self) -> None:
      if isinstance(self.focused, ListView):
        self.focused.action_cursor_down()

    def action_cursor_up(self) -> None:
      if isinstance(self.focused, ListView):
        self.focused.action_cursor_up()

    def action_focus_left(self) -> None:
      if self.focused and self.focused.id == "handler-list":
        self.query_one("#mime-list", ListView).focus()
        self.search_target = "mime"
      else:
        self.query_one("#mime-list", ListView).focus()
        self.search_target = "mime"

    def action_focus_right(self) -> None:
      self.query_one("#handler-list", ListView).focus()
      self.search_target = "handler"

    def action_focus_search(self) -> None:
      if self.focused and self.focused.id == "handler-list":
        self.search_target = "handler"
        self.query_one("#pane-search", Input).placeholder = "Search handlers"
      else:
        self.search_target = "mime"
        self.query_one("#pane-search", Input).placeholder = "Search MIME types"
      self.query_one("#pane-search", Input).focus()

    def action_set_default(self) -> None:
      mime_type = self._current_mime_type()
      desktop_id = self._current_handler_id()
      if mime_type is None or desktop_id is None:
        self._set_status("Select a MIME type and handler first.")
        return
      self.repository.set_default(mime_type, desktop_id)
      self._reload_handler_list(mime_type)
      self._refresh_preview()

    def action_toggle_added(self) -> None:
      mime_type = self._current_mime_type()
      desktop_id = self._current_handler_id()
      if mime_type is None or desktop_id is None:
        self._set_status("Select a MIME type and handler first.")
        return
      enabled = self.repository.toggle_added(mime_type, desktop_id)
      self._reload_handler_list(mime_type)
      self._refresh_preview()
      self._set_status(f"{'Added' if enabled else 'Removed'} explicit handler {desktop_id} for {mime_type}")

    def action_remove_handler(self) -> None:
      mime_type = self._current_mime_type()
      desktop_id = self._current_handler_id()
      if mime_type is None or desktop_id is None:
        self._set_status("Select a MIME type and handler first.")
        return
      self.repository.remove_handler(mime_type, desktop_id)
      self._reload_handler_list(mime_type)
      self._refresh_preview()
      self._set_status(f"Removed explicit handler {desktop_id} from {mime_type}")

    def action_toggle_removed(self) -> None:
      mime_type = self._current_mime_type()
      desktop_id = self._current_handler_id()
      if mime_type is None or desktop_id is None:
        self._set_status("Select a MIME type and handler first.")
        return
      enabled = self.repository.toggle_removed(mime_type, desktop_id)
      self._reload_handler_list(mime_type)
      self._refresh_preview()
      self._set_status(f"{'Blocked' if enabled else 'Unblocked'} {desktop_id} for {mime_type}")

    def action_toggle_override(self) -> None:
      mime_type = self._current_mime_type()
      desktop_id = self._current_handler_id()
      if mime_type is None or desktop_id is None:
        self._set_status("Select a MIME type and handler first.")
        return
      enabled = self.repository.toggle_override(mime_type, desktop_id)
      self._reload_handler_list(mime_type)
      self._refresh_preview()
      self._set_status(
        f"{'Stripped' if enabled else 'Restored'} MIME claim {mime_type} on {desktop_id}"
      )

    def action_refresh_preview(self) -> None:
      self._refresh_preview()

    def action_write_file(self) -> None:
      def handle_confirm(confirmed: bool) -> None:
        if not confirmed:
          self._set_status("Write cancelled.")
          return
        self._refresh_preview()
        write_nix_module(self.repository.output_path, self.preview_text)
        self._set_status(f"Wrote {self.repository.output_path}")

      self.push_screen(ConfirmWriteScreen(), handle_confirm)

    def action_show_help(self) -> None:
      self.push_screen(HelpScreen())
