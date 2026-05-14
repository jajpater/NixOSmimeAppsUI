from nixosmimeappsui.models import DeclarativeState, DesktopEntry, OverrideRule
from nixosmimeappsui.nixgen import render_nix_module


def test_render_nix_module_contains_sections() -> None:
    state = DeclarativeState(
      mime_defaults={"application/pdf": ["org.gnome.Evince.desktop"]},
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
        mime_types=("application/pdf", "text/html", "x-scheme-handler/http"),
        source_path="/tmp/com.brave.Browser.desktop",
      )
    }

    rendered = render_nix_module(state, entries)

    assert 'mimeDefaults = {' in rendered
    assert '"application/pdf" = [ "org.gnome.Evince.desktop" ];' in rendered
    assert '"application/pdf" = [ "com.brave.Browser.desktop" ];' in rendered
    assert '"com.brave.Browser.desktop" = [ "text/html" "x-scheme-handler/http" ];' in rendered
