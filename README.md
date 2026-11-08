# Counter-Survivors

Ego-Shooter im Stil von Counter-Strike 1.6, der sich wie Vampire Survivors spielt: laufen und schauen, die Waffen feuern selbst, sobald ein Terrorist in Sicht ist. Gebaut fürs iPhone (Safari, quer), läuft auch auf iPad und PC. Jede Seite ist eine einzelne HTML-Datei: Vanilla-JS, WebGL2, keine Bibliotheken, kein Build-Schritt beim Spielen.

## Spielen

- **Spiel:** https://olfbert.github.io/countersurvivor/
- **Modelltest** (alle Spielermodelle, Animationen, Horden-Stresstest): https://olfbert.github.io/countersurvivor/modeltest.html

## Stand

| Version | Phase | Inhalt |
| --- | --- | --- |
| v0.3 | Phase 3 · Survivors-Loop | 15-Minuten-Runde mit Countdown; Geld als Erfahrung (Scheine einsammeln); Level-Up öffnet das Kaufmenü mit 3 Angeboten und CZ-Icons; 8 Waffen (USP, Messer, Glock, Desert Eagle, MP5, M3, AK-47, HE-Granate) und 6 Ausrüstungen (Kevlar, Helm, Laufschuhe, Schnellladen, Hohlspitz, Defuse-Kit) mit Stufen; Wellen mit wachsendem Typ-Mix, Elites, Guerilla-Schützen, Militia-Bomber; Boss bei 5:00 (Der Riese) und 10:00 (Der Bombenleger); Pickups und Waffenkisten; Sieg- und Niederlagen-Auswertung pro Waffe; schärfere Darstellung |
| v0.2 | Phase 2 · Erste Horde | Terroristen (5 Modelle) mit Lauf-, Messer- und Todesanimationen, beleuchtet aus den Lightmaps; Wegnetz automatisch aus der Map (16er-Raster, Ebenen, Stufen) mit Flow-Field zum Spieler; Spawns außer Sicht; USP mit Autoshoot auf das fadenkreuznächste sichtbare Ziel (Magazin, Nachladen, Headshots); Messer rundum; Spielertod mit Todeskamera; Testmenü (Gegnerzahl, Unverwundbar) |
| v0.1 | Phase 1 · de_dust begehbar | Map aus der BSP mit Original-Texturen, Lightmaps und Himmel; CS-Bewegung (250 u/s, Reibung, Beschleunigung, Stufen bis 18 Einheiten, Springen, Luftsteuerung); Kollision über die Clip-Hulls der Map; Touch-Steuerung; Teleport zu CT-Spawn, T-Spawn, Bombsite A/B |
| – | Modelltest | 11 Spielermodelle mit GPU-Skinning und Instancing, 14 Animationen, bis 600 Gegner |

Nächste Phase: **Phase 4 · CS-Seele** (Radar, Bomben-Event auf A/B, Sounds, Killfeed, Titel mit Kamerafahrt, Teamwahl).

## Steuerung

Geschossen wird automatisch: Schusswaffen treffen den sichtbaren Gegner, der dem Fadenkreuz am nächsten ist; Messer und Granaten wirken unabhängig vom Blick. Gegner lassen Geld fallen – einsammeln füllt die Leiste oben, ein Level-Up öffnet das Kaufmenü.

- **iPhone/iPad:** linker Daumen laufen (Joystick erscheint dort, wo du tippst), rechter Daumen umschauen, Knopf rechts unten springen, ☰ für Pause, Teleport und Einstellungen.
- **PC:** WASD laufen, Maus schauen (Klick ins Bild fängt die Maus), Leertaste springen, Shift gehen, Esc Pause.

## Aufbau

```
index.html            Spiel (gebaut, mit eingebettetem Map-Paket)
modeltest.html        Modelltest (gebaut, mit eingebettetem Modell-Paket)
src/                  Vorlagen der Seiten (Code ohne Daten)
tools/convert_mdl.py  GoldSrc-MDL -> kompaktes Modell-Paket (Mesh, Textur-Atlas, Animationen)
tools/pack_map.py     BSP + WAD + Himmel -> Map-Paket (nur benutzte Texturen)
tools/skymatch.py     ordnet Himmelsbilder per Kantenabgleich den Würfelseiten zu
tools/pack_icons.py   Waffen-/Ausrüstungs-Icons (VGUI/XGUI) und Kisten-Textur als JSON
tools/build.py        setzt Pakete (Base64/JSON) und Version in eine Vorlage ein
```

Bauen (Pfade zu den eigenen Spieldateien anpassen):

```
python3 tools/pack_map.py de_dust_cz.bsp czde_dust.wad himmel/ map.bin && gzip -9 -k map.bin
python3 tools/convert_mdl.py models/ czde_dust.wad models.bin terror,leet,arctic,guerilla,militia && gzip -9 -k models.bin
python3 tools/pack_icons.py gfx/ czde_dust.wad icons.json
python3 tools/build.py src/game.template.html index.html 0.3 PACK=map.bin.gz MODELS=models.bin.gz ICONS=@icons.json
```

Die BSP wird erst im Browser gelesen (Geometrie, Lightmaps, Kollision, Spawns, Bombsites). Weitere Maps sind damit später nur ein neues Datenpaket.

## Hinweis zu den Spieldateien

Map, Texturen, Himmel und Spielermodelle stammen von Valve (Counter-Strike / Condition Zero) und stecken eingebettet in den gebauten HTML-Dateien. Gedacht für private Tests; die Rechte liegen bei Valve.
