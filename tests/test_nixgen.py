from nixosmimeappsui.models import DeclarativeState, DesktopEntry, OverrideRule
from nixosmimeappsui.nixgen import render_nix_module


def test_render_nix_module_contains_sections() -> None:
    state = DeclarativeState(
      mime_defaults={"application/pdf": ["org.gnome.Evince.desktop"]},
      mime_added={"application/pdf": ["org.gnome.Evince.desktop", "sioyek.desktop"]},
      mime_removed={"application/pdf": ["com.brave.Browser.desktop"]},
      desktop_overrides={
        "com.brave.Browser.desktop": OverrideRule(
          desktop_id="com.brave.Browser.desktop",
          allowed_mime_types=["text/html", "x-scheme-handler/http"],
        )
      },
    )
    entries = {
      "com.brave.Browser.desktop": DesktopEntry(
        desktop_id="com.brave.Browser.desktop",
        name="Brave",
        exec="brave %U",
        icon="brave-browser",
        generic_name="Web Browser",
        comment="Access the Internet",
        terminal=False,
        startup_notify=True,
        categories="Network;WebBrowser;",
        mime_types=("application/pdf", "text/html", "x-scheme-handler/http"),
        source_path="/tmp/com.brave.Browser.desktop",
        original_text="[Desktop Entry]\nName=Brave\nMimeType=application/pdf;text/html;x-scheme-handler/http;\nExec=brave %U\n",
      )
    }

    rendered = render_nix_module(state, entries)

    assert 'mimeDefaults = {' in rendered
    assert '"application/pdf" = [ "org.gnome.Evince.desktop" ];' in rendered
    assert 'mimeAdded = {' in rendered
    assert '"application/pdf" = [ "org.gnome.Evince.desktop" "sioyek.desktop" ];' in rendered
    assert '"application/pdf" = [ "com.brave.Browser.desktop" ];' in rendered
    assert "associations.added = mimeAdded;" in rendered
    assert '"com.brave.Browser.desktop" = [ "text/html" "x-scheme-handler/http" ];' in rendered
    assert "MimeType=text/html;x-scheme-handler/http;" in rendered
