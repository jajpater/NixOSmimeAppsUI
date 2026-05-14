# NixOSmimeAppsUI

`NixOSmimeAppsUI` is a terminal UI for managing MIME associations declaratively in a NixOS/Home Manager repository.

## Scope

This v1 is intentionally opinionated:

- It is designed around a NixOS repo shaped like `/home/jajpater/Develop/nixos-config`.
- It uses a tool-managed Nix file as its source of truth.
- It focuses on MIME-first editing: choose a MIME type, set a default app, block noisy handlers, and optionally strip specific MIME claims from desktop entries.

## Current behavior

- Discovers `.desktop` files from common XDG application directories.
- Builds a MIME-to-handler index from `MimeType=...` entries.
- Stores declarative state in `home/modules/generated-mimeapps.nix` by default.
- Shows a Textual TUI with vim-style navigation and a live Nix preview.

## Run

```bash
python -m nixosmimeappsui.cli
```

Or with Nix:

```bash
nix run
```

## Keybindings

- `j` / `k`: move in the focused list
- `h` / `l`: switch between MIME list and handler list
- `/`: focus MIME search
- `d`: set selected handler as default
- `x`: toggle blocked handler for selected MIME/handler pair
- `o`: toggle MIME stripping override for selected MIME/handler pair
- `s`: refresh Nix preview
- `w`: write generated Nix file
- `q`: quit

## Output

The generated Nix file contains three sections:

- `mimeDefaults`
- `mimeRemoved`
- `desktopOverrides`

The file is intended to be imported by a hand-written Home Manager module later.
