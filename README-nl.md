# NixOSmimeAppsUI

`NixOSmimeAppsUI` is een terminalprogramma om MIME-koppelingen declaratief te
beheren in een NixOS/Home Manager repo.

## Wat dit programma wel en niet doet

Dit programma maakt **niet** je hele MIME-config opnieuw.

Het schrijft alleen een bestand met jouw wijzigingen:

- `generated-mimeapps.nix`

Dat bestand is dus alleen een **aanvulling** op je bestaande config.

Kort gezegd:

- wat je **niet** in de TUI aanpast, blijft zoals het al was
- wat je **wel** aanpast, komt in `generated-mimeapps.nix`
- dat bestand is dus geen complete lijst van alles

Als je in `generated-mimeapps.nix` maar een paar filetypes ziet, is dat normaal.
Dat betekent alleen dat je tot nu toe maar een paar filetypes via de tool hebt
aangepast.

## Hoe dit samenwerkt met je bestaande Nix-config

Je hebt al een gewone handgeschreven config, bijvoorbeeld:

- `home/modules/xdg.nix`

Daarnaast gebruikt deze tool:

- `home/modules/generated-mimeapps.nix`

Denk eraan als twee lagen:

1. Je gewone handgeschreven basisconfig
2. De wijzigingen uit deze tool

Dus:

- `xdg.nix` blijft je basis
- `generated-mimeapps.nix` bevat alleen de tool-wijzigingen
- als een MIME type niet in `generated-mimeapps.nix` staat, blijft je gewone
  config daarvoor gelden

## Wat betekenen die blokken?

### `mimeDefaults`

Dit bepaalt welke app standaard opent.

Voorbeeld:

```nix
"application/pdf" = [ "org.gnome.Evince.desktop" ];
```

Dat betekent: PDF opent standaard met Evince.

### `mimeAdded`

Dit voegt apps toe als geldige keuze voor een MIME type.

Gebruik dit als je wilt dat een app zichtbaar wordt bij "Openen met", ook als
die app daar eerst niet stond.

### `mimeRemoved`

Dit haalt apps weg uit de koppelingen voor dat MIME type.

Gebruik dit als een app steeds opduikt bij een bestandstype terwijl je dat niet
wilt.

### `desktopOverrides`

Dit is voor een ander probleem.

Soms claimt een app in zijn eigen `.desktop` bestand dat hij een bestandstype
kan openen, terwijl je dat niet wilt. Bijvoorbeeld: een browser die zegt dat
hij PDFs kan openen.

Dan is alleen `mimeapps.list` aanpassen soms niet genoeg.

Met `desktopOverrides` maakt de tool een lokale override van die `.desktop`
entry en verandert alleen de `MimeType=` regel.

Simpel gezegd:

- `mimeDefaults` / `mimeAdded` / `mimeRemoved` gaan over koppelingen
- `desktopOverrides` gaat over wat een app zelf beweert te kunnen openen

### `desktopMetadata`

Dit is hulpdata die nodig is om zo'n override-bestand te maken.

Als `desktopOverrides` leeg is, is `desktopMetadata` meestal ook leeg. Dan doet
dat deel dus niets.

## Belangrijk om te onthouden

Je hebt hier twee niveaus:

1. Welke app standaard of als keuze gebruikt wordt
2. Welke filetypes een app zelf claimt te ondersteunen

Meestal heb je alleen niveau 1 nodig.

Niveau 2 heb je alleen nodig voor irritante of verkeerde registraties, zoals
een browser die zich als PDF-lezer aanmeldt.

## Belangrijkste toetsen

- `j` / `k`: omhoog/omlaag
- `h` / `l`: wisselen tussen MIME-lijst en handler-lijst
- `/`: zoeken in de lijst waar je nu op staat
- `a`: app expliciet toevoegen als handler
- `r`: expliciet toegevoegde handler weer verwijderen
- `d`: geselecteerde app standaard maken
- `x`: handler blokkeren/verwijderen uit associaties
- `o`: MIME-claim uit een desktop entry strippen
- `w`: wijzigingen wegschrijven naar `generated-mimeapps.nix`
- `q`: afsluiten

## Wat moet je doen na een wijziging?

1. Start de tool
2. Pas dingen aan
3. Druk op `w`
4. Rebuild je NixOS/Home Manager config

Bijvoorbeeld:

```bash
sudo nixos-rebuild switch --flake .#laptop
```

Zonder rebuild verandert je systeemconfig niet blijvend.

## Kleine web UI

Er is ook een kleine web UI.

Start die zo:

```bash
nix run -- --web
```

Open daarna:

```text
http://127.0.0.1:8787
```

Die web UI houdt het bewust simpel:

- lijst met MIME types
- zoekveld voor MIME types
- lijst met handlers
- zoekveld voor handlers
- knoppen voor default / added / removed / override
- live preview van de gegenereerde Nix
- save-knop

De web UI gebruikt dezelfde logica als de TUI. Het resultaat is dus hetzelfde
type `generated-mimeapps.nix`.
