from __future__ import annotations

import argparse
from pathlib import Path

from .app import NixOSMimeAppsUI
from .state import DEFAULT_OUTPUT_RELATIVE, DEFAULT_REPO_ROOT
from .web import WebUI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Declarative MIME app manager for a NixOS/Home Manager repo")
    parser.add_argument(
      "--repo-root",
      type=Path,
      default=DEFAULT_REPO_ROOT,
      help="Path to the target NixOS repo",
    )
    parser.add_argument(
      "--output-relative",
      type=Path,
      default=DEFAULT_OUTPUT_RELATIVE,
      help="Path inside the repo where the generated Nix file should be written",
    )
    parser.add_argument(
      "--web",
      action="store_true",
      help="Run the minimal local web UI instead of the Textual TUI",
    )
    parser.add_argument(
      "--host",
      default="127.0.0.1",
      help="Host for web mode",
    )
    parser.add_argument(
      "--port",
      type=int,
      default=8789,
      help="Port for web mode",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.web:
      app = WebUI(repo_root=args.repo_root, output_relative=args.output_relative)
      app.serve(host=args.host, port=args.port)
    else:
      app = NixOSMimeAppsUI(repo_root=args.repo_root, output_relative=args.output_relative)
      app.run()


if __name__ == "__main__":
    main()
