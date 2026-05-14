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

## Beginner explanation

This tool does **not** generate your full MIME setup.

It writes a file called `generated-mimeapps.nix` that contains only the
changes you made in the TUI.

That means:

- if a MIME type is **not** listed in `generated-mimeapps.nix`, the tool did
  not change it
- your normal hand-written Nix/Home Manager config is still the main setup
- the generated file is a **delta**, not a full replacement

In your NixOS repo this is meant to work together with your existing
`home/modules/xdg.nix`:

- `xdg.nix` stays your hand-written base config
- `generated-mimeapps.nix` adds tool-managed changes on top
- if both files mention the same MIME type, the generated file becomes the
  tool-managed version for that MIME type

So if you only see this:

```nix
mimeDefaults = {
  "text/markdown" = [ "LazyVim-neovide.desktop" ];
};
```

that does **not** mean this is your whole MIME configuration.

It only means:

- you changed `text/markdown` in the TUI
- the tool has not written changes for other MIME types
- all other MIME types still come from your normal config unless you edit them

## What the generated sections mean

### `mimeDefaults`

This sets the default app for a MIME type.

Example:

```nix
"application/pdf" = [ "org.gnome.Evince.desktop" ];
```

This means PDFs should open by default in Evince.

### `mimeAdded`

This adds apps as valid choices for a MIME type.

Use this when you want an app to appear in "Open With", even if it is not
currently offered there.

### `mimeRemoved`

This removes apps from the association list for that MIME type.

Use this when an app keeps showing up for a file type and you do not want it
there.

### `desktopOverrides`

This is for a different problem.

Sometimes an app advertises the wrong MIME types in its own `.desktop` file.
For example, a browser may claim it can open PDFs.

In that case, changing only `mimeapps.list` is not always enough. A desktop
override lets the tool generate a local replacement `.desktop` file that keeps
the app but rewrites the `MimeType=` line.

Use this only when you want to change what the app itself claims to support.

### `desktopMetadata`

This is helper data used to build those rewritten `.desktop` files.

If `desktopOverrides` is empty, then `desktopMetadata` will usually also be
empty and nothing special happens.

## Important mental model

There are two layers:

1. XDG association rules
   This is `mimeDefaults`, `mimeAdded`, and `mimeRemoved`.
   This controls defaults and choices.

2. Desktop entry rewriting
   This is `desktopOverrides`.
   This changes what an app itself claims to handle.

Most of the time you only need layer 1.
Use layer 2 only for noisy or wrong app registrations.

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
- `/`: search the currently focused pane
- `a`: toggle explicit added association for selected app
- `r`: remove explicit handler from the selected MIME type
- `d`: set selected handler as default
- `x`: toggle blocked handler for selected MIME/handler pair
- `o`: toggle MIME stripping override for selected MIME/handler pair
- `s`: refresh Nix preview
- `w`: write generated Nix file
- `q`: quit

## Output

The generated Nix file contains three sections:

- `mimeDefaults`
- `mimeAdded`
- `mimeRemoved`
- `desktopOverrides`

It may also contain `desktopMetadata`, which is support data for generated
desktop-entry overrides.

The file is intended to be imported by a hand-written Home Manager module later.
