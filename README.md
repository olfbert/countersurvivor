# Counter-Survivors

Ego-Shooter im Stil von Counter-Strike 1.6, der sich wie Vampire Survivors spielt: laufen und schauen, die Waffen feuern selbst, sobald ein Terrorist in Sicht ist. Gebaut fürs iPhone (Safari, quer), läuft auch auf iPad und PC. Jede Seite ist eine einzelne HTML-Datei: Vanilla-JS, WebGL2, keine Bibliotheken, kein Build-Schritt beim Spielen.

## Spielen

- **Spiel:** https://olfbert.github.io/countersurvivor/
- **Modelltest** (alle Spielermodelle, Animationen, Horden-Stresstest): https://olfbert.github.io/countersurvivor/modeltest.html

## Stand

| Version | Phase | Inhalt |
| --- | --- | --- |
| v0.1 | Phase 1 · de_dust begehbar | Map aus der BSP mit Original-Texturen, Lightmaps und Himmel; CS-Bewegung (250 u/s, Reibung, Beschleunigung, Stufen bis 18 Einheiten, Springen, Luftsteuerung); Kollision über die Clip-Hulls der Map; Touch-Steuerung; Teleport zu CT-Spawn, T-Spawn, Bombsite A/B |
| – | Modelltest | 11 Spielermodelle mit GPU-Skinning und Instancing, 14 Animationen, bis 600 Gegner |

Nächste Phase: **Phase 2 · Erste Horde** (Terroristen mit Wegfindung, Spawns, USP und Messer mit Autoshoot, Schaden, Tod).

## Steuerung

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
tools/build.py        setzt Paket (Base64) und Version in eine Vorlage ein
```

Bauen (Pfade zu den eigenen Spieldateien anpassen):

```
python3 tools/pack_map.py de_dust_cz.bsp czde_dust.wad himmel/ map.bin && gzip -9 -k map.bin
python3 tools/build.py src/game.template.html map.bin.gz index.html 0.1
```

Die BSP wird erst im Browser gelesen (Geometrie, Lightmaps, Kollision, Spawns, Bombsites). Weitere Maps sind damit später nur ein neues Datenpaket.

## Hinweis zu den Spieldateien

Map, Texturen, Himmel und Spielermodelle stammen von Valve (Counter-Strike / Condition Zero) und stecken eingebettet in den gebauten HTML-Dateien. Gedacht für private Tests; die Rechte liegen bei Valve.
