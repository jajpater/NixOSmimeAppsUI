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
    """

    BINDINGS = [
      Binding("q", "quit", "Quit"),
      Binding("j", "cursor_down", "Down", show=False),
      Binding("k", "cursor_up", "Up", show=False),
      Binding("h", "focus_left", "Left", show=False),
      Binding("l", "focus_right", "Right", show=False),
      Binding("/", "focus_search", "Search"),
      Binding("d", "set_default", "Set Default"),
      Binding("x", "toggle_removed", "Toggle Block"),
      Binding("o", "toggle_override", "Toggle Override"),
      Binding("s", "refresh_preview", "Preview"),
      Binding("w", "write_file", "Write"),
    ]

    filtered_mime_types: reactive[list[str]] = reactive(list)

    def __init__(self, repo_root: Path | None = None, output_relative: Path | None = None):
      super().__init__()
      self.repository = MimeRepository(
        repo_root=repo_root or DEFAULT_REPO_ROOT,
        output_relative=output_relative or DEFAULT_OUTPUT_RELATIVE,
      )
      self.filtered_mime_types = self.repository.mime_types
      self.preview_text = ""

    def compose(self) -> ComposeResult:
      yield Header()
      yield Input(placeholder="Search MIME types", id="mime-search")
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
      self.query_one("#mime-search", Input).blur()
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
      if self.repository.current_default_for(mime_type) == desktop_id:
        flags.append("default")
      if self.repository.is_removed(mime_type, desktop_id):
        flags.append("blocked")
      override = self.repository.override_for(desktop_id)
      if override is not None and mime_type not in override.allowed_mime_types:
        flags.append("stripped")
      suffix = f" [{' | '.join(flags)}]" if flags else ""
      return f"{entry.name} ({desktop_id}){suffix}"

    def _reload_handler_list(self, mime_type: str) -> None:
      handler_list = self.query_one("#handler-list", ListView)
      handler_list.clear()
      for entry in self.repository.handlers_for(mime_type):
        handler_list.append(HandlerItem(entry.desktop_id, self._handler_label(mime_type, entry.desktop_id)))
      if self.repository.handlers_for(mime_type):
        handler_list.index = 0

    def _refresh_preview(self) -> None:
      self.preview_text = render_nix_module(self.repository.state, self.repository.entries)
      self.query_one("#preview", Static).update(self.preview_text)
      self._set_status(f"Preview refreshed for {self.repository.output_path}")

    def on_input_changed(self, event: Input.Changed) -> None:
      query = event.value.strip().lower()
      if not query:
        self.filtered_mime_types = self.repository.mime_types
      else:
        self.filtered_mime_types = [
          mime_type for mime_type in self.repository.mime_types
          if query in mime_type.lower()
        ]
      self._reload_mime_list()

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
      else:
        self.query_one("#mime-list", ListView).focus()

    def action_focus_right(self) -> None:
      self.query_one("#handler-list", ListView).focus()

    def action_focus_search(self) -> None:
      self.query_one("#mime-search", Input).focus()

    def action_set_default(self) -> None:
      mime_type = self._current_mime_type()
      desktop_id = self._current_handler_id()
      if mime_type is None or desktop_id is None:
        self._set_status("Select a MIME type and handler first.")
        return
      self.repository.set_default(mime_type, desktop_id)
      self._reload_handler_list(mime_type)
      self._refresh_preview()

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
