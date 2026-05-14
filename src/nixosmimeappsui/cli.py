from __future__ import annotations

import argparse
from pathlib import Path

from .app import NixOSMimeAppsUI
from .state import DEFAULT_OUTPUT_RELATIVE, DEFAULT_REPO_ROOT


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
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    app = NixOSMimeAppsUI(repo_root=args.repo_root, output_relative=args.output_relative)
    app.run()


if __name__ == "__main__":
    main()
