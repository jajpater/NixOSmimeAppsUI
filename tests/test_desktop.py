from pathlib import Path

from nixosmimeappsui.desktop import parse_desktop_entry


def test_parse_desktop_entry_reads_mime_types(tmp_path: Path) -> None:
    desktop_file = tmp_path / "viewer.desktop"
    desktop_file.write_text(
      "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=Viewer",
        "Exec=viewer %U",
        "MimeType=application/pdf;text/plain;",
      ]),
      encoding="utf-8",
    )

    entry = parse_desktop_entry(desktop_file)

    assert entry is not None
    assert entry.desktop_id == "viewer.desktop"
    assert entry.generic_name == ""
    assert entry.comment == ""
    assert entry.mime_types == ("application/pdf", "text/plain")
