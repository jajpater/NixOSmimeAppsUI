from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from wsgiref.simple_server import make_server

from .nixgen import render_nix_module, write_nix_module
from .state import DEFAULT_OUTPUT_RELATIVE, DEFAULT_REPO_ROOT, MimeRepository


def _h(value: str) -> str:
    return html.escape(value, quote=True)


class WebUI:
    def __init__(self, repo_root: Path | None = None, output_relative: Path | None = None):
        self.repository = MimeRepository(
            repo_root=repo_root or DEFAULT_REPO_ROOT,
            output_relative=output_relative or DEFAULT_OUTPUT_RELATIVE,
        )
        self.status = "Ready."

    def serve(self, host: str = "127.0.0.1", port: int = 8787) -> None:
        with make_server(host, port, self.wsgi_app) as httpd:
            print(f"NixOSmimeAppsUI web UI listening on http://{host}:{port}")
            httpd.serve_forever()

    def wsgi_app(self, environ, start_response):
        method = environ["REQUEST_METHOD"].upper()
        parsed = urlparse(environ.get("PATH_INFO", "/"))
        query = parse_qs(environ.get("QUERY_STRING", ""))

        if method == "POST" and parsed.path == "/action":
            size = int(environ.get("CONTENT_LENGTH") or "0")
            body = environ["wsgi.input"].read(size).decode("utf-8")
            form = parse_qs(body)
            location = self.handle_action(form)
            start_response("303 See Other", [("Location", location)])
            return [b""]

        if parsed.path != "/":
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
            return [b"Not found"]

        content = self.render_index(query)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [content.encode("utf-8")]

    def handle_action(self, form: dict[str, list[str]]) -> str:
        action = form.get("action", [""])[0]
        mime_type = form.get("mime", [""])[0]
        desktop_id = form.get("desktop_id", [""])[0]
        mime_q = form.get("mime_q", [""])[0]
        handler_q = form.get("handler_q", [""])[0]

        if action == "save":
            content = render_nix_module(self.repository.state, self.repository.entries)
            write_nix_module(self.repository.output_path, content)
            self.status = f"Wrote {self.repository.output_path}"
        elif mime_type and desktop_id:
            if action == "set_default":
                self.repository.set_default(mime_type, desktop_id)
                self.status = f"Set default for {mime_type} to {desktop_id}"
            elif action == "toggle_added":
                enabled = self.repository.toggle_added(mime_type, desktop_id)
                self.status = f"{'Added' if enabled else 'Removed'} explicit handler {desktop_id} for {mime_type}"
            elif action == "remove_handler":
                self.repository.remove_handler(mime_type, desktop_id)
                self.status = f"Removed explicit handler {desktop_id} from {mime_type}"
            elif action == "toggle_removed":
                enabled = self.repository.toggle_removed(mime_type, desktop_id)
                self.status = f"{'Blocked' if enabled else 'Unblocked'} {desktop_id} for {mime_type}"
            elif action == "toggle_override":
                enabled = self.repository.toggle_override(mime_type, desktop_id)
                self.status = f"{'Stripped' if enabled else 'Restored'} MIME claim {mime_type} on {desktop_id}"

        params = {}
        if mime_type:
            params["mime"] = mime_type
        if mime_q:
            params["mime_q"] = mime_q
        if handler_q:
            params["handler_q"] = handler_q
        return "/?" + urlencode(params)

    def render_index(self, query: dict[str, list[str]]) -> str:
        mime_q = query.get("mime_q", [""])[0].strip().lower()
        handler_q = query.get("handler_q", [""])[0].strip().lower()
        selected_mime = query.get("mime", [""])[0]

        mime_types = self.repository.mime_types
        if mime_q:
            mime_types = [mime for mime in mime_types if mime_q in mime.lower()]
        if not selected_mime and mime_types:
            selected_mime = mime_types[0]

        handlers_html = "<p>Select a MIME type.</p>"
        if selected_mime:
            handlers = self.repository.handlers_for(selected_mime)
            if handler_q:
                handlers = [
                    entry for entry in handlers
                    if handler_q in entry.desktop_id.lower() or handler_q in entry.name.lower()
                ]
            handlers_html = self.render_handlers(selected_mime, handlers, mime_q, handler_q)

        preview = render_nix_module(self.repository.state, self.repository.entries)
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>NixOSmimeAppsUI</title>
  <style>
    body {{ font-family: sans-serif; margin: 0; padding: 0; }}
    .top {{ padding: 12px 16px; background: #f3f3f3; border-bottom: 1px solid #ddd; }}
    .status {{ margin-top: 8px; color: #333; }}
    .layout {{ display: grid; grid-template-columns: 1fr 2fr 2fr; gap: 16px; padding: 16px; }}
    .pane {{ border: 1px solid #ddd; padding: 12px; overflow: auto; }}
    .mime-link {{ display: block; padding: 6px 8px; text-decoration: none; color: inherit; border-radius: 4px; }}
    .mime-link.active {{ background: #e8eefc; }}
    .handler {{ border: 1px solid #e4e4e4; margin-bottom: 8px; padding: 8px; border-radius: 6px; }}
    .flags {{ color: #666; font-size: 0.95em; margin-top: 4px; }}
    form.inline {{ display: inline-block; margin: 4px 6px 0 0; }}
    button {{ cursor: pointer; }}
    pre {{ white-space: pre-wrap; word-break: break-word; }}
    input[type=text] {{ width: 100%; box-sizing: border-box; margin-bottom: 8px; }}
  </style>
</head>
<body>
  <div class="top">
    <strong>NixOSmimeAppsUI Web</strong>
    <form method="post" action="/action" class="inline">
      <input type="hidden" name="action" value="save">
      <button type="submit">Save generated-mimeapps.nix</button>
    </form>
    <div class="status">{_h(self.status)}</div>
  </div>
  <div class="layout">
    <div class="pane">
      <h3>MIME types</h3>
      <form method="get" action="/">
        <input type="text" name="mime_q" value="{_h(mime_q)}" placeholder="Search MIME types">
      </form>
      {self.render_mime_list(mime_types, selected_mime, mime_q, handler_q)}
    </div>
    <div class="pane">
      <h3>Handlers</h3>
      <form method="get" action="/">
        <input type="hidden" name="mime" value="{_h(selected_mime)}">
        <input type="hidden" name="mime_q" value="{_h(mime_q)}">
        <input type="text" name="handler_q" value="{_h(handler_q)}" placeholder="Search handlers">
      </form>
      {handlers_html}
    </div>
    <div class="pane">
      <h3>Generated Nix Preview</h3>
      <pre>{_h(preview)}</pre>
    </div>
  </div>
</body>
</html>"""

    def render_mime_list(self, mime_types: list[str], selected_mime: str, mime_q: str, handler_q: str) -> str:
        items = []
        for mime_type in mime_types:
            params = {"mime": mime_type}
            if mime_q:
                params["mime_q"] = mime_q
            if handler_q:
                params["handler_q"] = handler_q
            active = " active" if mime_type == selected_mime else ""
            items.append(
                f'<a class="mime-link{active}" href="/?{urlencode(params)}">{_h(mime_type)}</a>'
            )
        return "".join(items) or "<p>No MIME types match this filter.</p>"

    def render_handlers(self, mime_type: str, handlers, mime_q: str, handler_q: str) -> str:
        if not handlers:
            return "<p>No handlers match this filter.</p>"

        blocks = []
        for entry in handlers:
            flags = []
            if self.repository.supports_mime(mime_type, entry.desktop_id):
                flags.append("supports")
            if self.repository.is_added(mime_type, entry.desktop_id):
                flags.append("added")
            if self.repository.current_default_for(mime_type) == entry.desktop_id:
                flags.append("default")
            if self.repository.is_removed(mime_type, entry.desktop_id):
                flags.append("blocked")
            override = self.repository.override_for(entry.desktop_id)
            if override is not None and mime_type not in override.allowed_mime_types:
                flags.append("stripped")
            if not self.repository.supports_mime(mime_type, entry.desktop_id) and not self.repository.is_added(mime_type, entry.desktop_id):
                flags.append("not-advertised")

            buttons = []
            for action, label in [
                ("set_default", "Set default"),
                ("toggle_added", "Toggle added"),
                ("remove_handler", "Remove explicit"),
                ("toggle_removed", "Toggle blocked"),
                ("toggle_override", "Toggle override"),
            ]:
                buttons.append(self.render_action_form(action, label, mime_type, entry.desktop_id, mime_q, handler_q))

            blocks.append(
                f"""
<div class="handler">
  <strong>{_h(entry.name)}</strong><br>
  <code>{_h(entry.desktop_id)}</code>
  <div class="flags">{_h(" | ".join(flags) if flags else "no flags")}</div>
  {''.join(buttons)}
</div>
"""
            )
        return "".join(blocks)

    def render_action_form(self, action: str, label: str, mime_type: str, desktop_id: str, mime_q: str, handler_q: str) -> str:
        hidden = [
            f'<input type="hidden" name="action" value="{_h(action)}">',
            f'<input type="hidden" name="mime" value="{_h(mime_type)}">',
            f'<input type="hidden" name="desktop_id" value="{_h(desktop_id)}">',
            f'<input type="hidden" name="mime_q" value="{_h(mime_q)}">',
            f'<input type="hidden" name="handler_q" value="{_h(handler_q)}">',
        ]
        return f'<form method="post" action="/action" class="inline">{"".join(hidden)}<button type="submit">{_h(label)}</button></form>'
