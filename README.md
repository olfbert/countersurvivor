# Counter-Survivors

Ego-Shooter im Stil von Counter-Strike 1.6, der sich wie Vampire Survivors spielt: laufen und schauen, die Waffen feuern selbst, sobald ein Terrorist in Sicht ist. Gebaut fürs iPhone (Safari, quer), läuft auch auf iPad und PC. Jede Seite ist eine einzelne HTML-Datei: Vanilla-JS, WebGL2, keine Bibliotheken, kein Build-Schritt beim Spielen.

## Spielen

- **Spiel:** https://olfbert.github.io/countersurvivor/
- **Modelltest** (alle Spielermodelle, Animationen, Horden-Stresstest): https://olfbert.github.io/countersurvivor/modeltest.html

## Stand

| Version | Phase | Inhalt |
| --- | --- | --- |
| v0.10.2 | Fix | Killfeed blieb in der zweiten Runde leer (Drossel-Zeit wurde beim Neustart nicht zurückgesetzt) |
| v0.10.1 | Ducken | Ducken wie in CS (halb so hoch, ein Drittel Tempo, Aufstehen nur mit Platz über dem Kopf): Touch-Knopf DUCKEN (an/aus) über SPRUNG, PC Strg oder C; Turm-Knopf rückt nach oben |
| v0.10 | Waffenhändler | Geld der Runde wandert aufs Konto (bleibt im Browser gespeichert); Waffenhändler im Hauptmenü mit dauerhaften Upgrades (Leben, Schaden, Geschäftssinn, Sammelradius, Kondition, viertes Angebot, zweites Leben) und freischaltbaren Startwaffen; „Hauptmenü“ im Pause- und Endbildschirm; Schwimmen (auch in func_water): Blickrichtung schwimmen, Springen = hoch und an der Kante raus, Unterwasser-Tönung |
| v0.9.5 | Neue Evolutionen | Geschützturm + Nachtsicht = **Aperture-Abwehr** (schwenkt ±90°, erfasst sofort, doppelter Schaden); Roomba + Defuse-Kit = **Kampf-Roomba** (zieht Geld aus 170 Einheiten an, 40 % schneller, verletzt Gegner beim Überfahren) |
| v0.9.4 | Zerstörbares | func_breakable geht kaputt: anschauen = draufschießen (wenn gerade kein Gegner im Visier ist), Explosionen zerstören mit; Splitter je nach Material (Glas, Holz, Metall, Computer …); Teile mit „bei Berührung/Draufstehen“ zerbrechen beim Anfassen; kommen zur nächsten Runde wieder |
| v0.9.3 | de_rats komplett | Packer übernimmt jetzt in die BSP eingebaute Texturen (de_rats: Dosen, Schränke, Fliesen …) und Himmel aus gfx/env (`--sky ordner name`); de_rats mit Original-Himmel |
| v0.9.2 | Leitern | Leitern hochklettern wie in CS (nach vorn drücken; Blick nach unten = runter; Springen = abspringen) |
| v0.9.1 | Feinschliff | cs_italy mit allen Texturen; Roomba startet langsamer (105 statt 190, Stufen bis 205) |
| v0.9 | Roomba & neue Maps | Roomba zum Kaufen: fährt übers Wegnetz zum nächsten Geldschein in Sicht und saugt ihn ein, sonst folgt er dir (Stufen: schneller, breiter, bis zu 3 Roombas; grün im Radar); Killfeed oben rechts (höchstens 5 Zeilen, normale Kills gedrosselt, Elites und Bosse immer); cs_747 raus, neu: cs_assault, cs_italy, de_rats; Wegnetz findet jetzt auch Treppen unter unsichtbaren Clip-Rampen (sonst kamen auf cs_italy keine Gegner) |
| v0.8.2 | Fixes | Turm wird richtig dargestellt (Außenhülle war teils unsichtbar, man sah ins Innere); auf Kisten, Fässern und anderen „Inseln“ ohne Weg kommen weiter Gegner: sie laufen zum Boden drumherum und schlagen nach oben |
| v0.8 | Geschützturm | Neue Waffe „Geschützturm“ (Portal-Sentry): mit dem Knopf TURM (PC: Taste T) vor dir hinstellen, klappt auf, sucht mit rotem Laser und feuert nur in einem 60°-Fächer nach vorn (±30°), sobald der Laser kurz auf dem Ziel liegt; bleibt stehen, Stufen bringen mehr Schaden, Reichweite, Feuerrate und bis zu 3 Türme gleichzeitig; Türme im Radar (hellblau); im Testmenü „Geschützturm geben“ |
| v0.7 | Sound | Original-CS-Sounds: jede Waffe mit eigenem Schuss, Nachladen, Messer, Granaten, C4 mit schneller werdendem Piepen, Treffer, Headshots, Todesschreie, Schritte (Sand oder Stein je nach Boden), Funksprüche zu Rundenstart, Sieg und Niederlage, Boss-Auftritte, Geisel-Rufe auf cs_747; Geräusche kommen räumlich von links/rechts und werden mit Abstand leiser; Lautstärke im Menü |
| v0.6 | Props & Radar | Echte Deko-Modelle in de_dust (Jeep, Lkw, 13 Fässer, 6 Markisen) statt Platzhalter-Boxen, beleuchtet vom Boden darunter; Radar oben rechts (dreht mit, Gegner rot, Elites orange, Boss groß, Kisten gelb; dunkler = andere Etage), für cs_747 aus der Original-Übersichtskarte (automatisch eingepasst), für de_dust beim Laden von oben gerendert; cs_747 jetzt mit allen Texturen; Teleport zu den Geiseln landet auf begehbarem Boden (vorher kamen dort keine Gegner); Radar im Menü abschaltbar |
| v0.5 | Mehr Maps | Map-Auswahl im Startbildschirm; zweite Map cs_747 (Flugzeug, Geiselrettung) wird aus `maps/` nachgeladen; Türen stehen offen, Teleport zu Geiseln und Rettungszone; Ersatzhimmel für Maps ohne Himmelsbilder; **Fix:** bei vielen Gegnern hinter Wänden hörten die Waffen auf zu schießen |
| v0.4 | Mehr Waffen + Evolutionen | 6 neue Waffen (AWP, M249, Dual Elites, Flashbang, Rauchgranate, C4) und 3 neue Ausrüstungen (Headshot-Training, Nachtsicht, Magazinerweiterung) – zusammen 14 Waffen und 9 Ausrüstungen; 14 Evolutionen über Waffenkisten (z. B. Goldene AK, Wallbang-AWP, Messerwirbel, Giftnebel); Evolutionsliste im Menü; neue Schwierigkeitskurve (leichter Start, deutlich härteres Ende, stärkere Bosse, steilere XP-Kurve); Kollisionsboxen der fehlenden Deko-Modelle als Platzhalter sichtbar |
| v0.3 | Phase 3 · Survivors-Loop | 15-Minuten-Runde mit Countdown; Geld als Erfahrung (Scheine einsammeln); Level-Up öffnet das Kaufmenü mit 3 Angeboten und CZ-Icons; 8 Waffen (USP, Messer, Glock, Desert Eagle, MP5, M3, AK-47, HE-Granate) und 6 Ausrüstungen (Kevlar, Helm, Laufschuhe, Schnellladen, Hohlspitz, Defuse-Kit) mit Stufen; Wellen mit wachsendem Typ-Mix, Elites, Guerilla-Schützen, Militia-Bomber; Boss bei 5:00 (Der Riese) und 10:00 (Der Bombenleger); Pickups und Waffenkisten; Sieg- und Niederlagen-Auswertung pro Waffe; schärfere Darstellung |
| v0.2 | Phase 2 · Erste Horde | Terroristen (5 Modelle) mit Lauf-, Messer- und Todesanimationen, beleuchtet aus den Lightmaps; Wegnetz automatisch aus der Map (16er-Raster, Ebenen, Stufen) mit Flow-Field zum Spieler; Spawns außer Sicht; USP mit Autoshoot auf das fadenkreuznächste sichtbare Ziel (Magazin, Nachladen, Headshots); Messer rundum; Spielertod mit Todeskamera; Testmenü (Gegnerzahl, Unverwundbar) |
| v0.1 | Phase 1 · de_dust begehbar | Map aus der BSP mit Original-Texturen, Lightmaps und Himmel; CS-Bewegung (250 u/s, Reibung, Beschleunigung, Stufen bis 18 Einheiten, Springen, Luftsteuerung); Kollision über die Clip-Hulls der Map; Touch-Steuerung; Teleport zu CT-Spawn, T-Spawn, Bombsite A/B |
| – | Modelltest | 11 Spielermodelle mit GPU-Skinning und Instancing, 14 Animationen, bis 600 Gegner |

Als Nächstes: Rest von **Phase 4 · CS-Seele** (Bomben-Event auf A/B, Killfeed, Titel, Teamwahl) und weitere Maps, sobald die Dateien da sind.

## Maps

| Map | Datei | Stand |
| --- | --- | --- |
| de_dust (Condition Zero) | in `index.html` eingebettet | vollständig, mit Deko-Modellen |
| cs_assault | `maps/cs_assault.bin` | vollständig texturiert; Himmel ist Ersatz (city1 fehlt) |
| cs_italy | `maps/cs_italy.bin` | vollständig texturiert (itsitaly.wad); Himmel Ersatz (green fehlt) |
| de_rats | `maps/de_rats_2001.bin` | vollständig: Küchen-Texturen stecken in der BSP selbst, Original-Himmel dusk |

Weitere Maps sind nur Daten: BSP + WADs (+ Himmel, Deko-Modelle, Übersichtskarte) packen, in `maps/` legen und in der Map-Liste der Vorlage eintragen. Nachgeladene Maps funktionieren nur online (GitHub Pages), nicht als lokale Datei.

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
tools/props.py        Deko-Modelle (cycler_sprite/env_model) -> statische Meshes + gemeinsamer Textur-Atlas
tools/overview.py     passt eine CS-Übersichtskarte (grüner Rand) automatisch an die Map an (fürs Radar)
tools/skymatch.py     ordnet Himmelsbilder per Kantenabgleich den Würfelseiten zu
tools/convert_roomba.py Roomba (Tinkercad-OBJ) -> kleines Mesh-Paket (int16, Schattierung im Shader)
tools/convert_turret.py Portal-Turm (SMD + PNG) -> Turm-Paket (starre Knochen, Aufklapp- und Feueranimation)
tools/pack_sounds.py  WAVs aus cstrike/sound -> Sound-Paket (8 Bit mono, Stille am Ende gekürzt)
tools/pack_icons.py   Waffen-/Ausrüstungs-Icons (VGUI/XGUI) und Kisten-Textur als JSON
tools/build.py        setzt Pakete (Base64/JSON) und Version in eine Vorlage ein
```

Bauen (Pfade zu den eigenen Spieldateien anpassen):

```
python3 tools/pack_map.py map.bin de_dust_cz.bsp --wad czde_dust.wad --wad all-in-one.wad --sky-dust himmel/ --props models/ && gzip -9 -k map.bin
python3 tools/pack_map.py cs_italy.bin cs_italy.bsp --wad itsitaly.wad --wad cstrike.wad --wad all-in-one.wad --props models/ && gzip -9 -c cs_italy.bin > maps/cs_italy.bin
python3 tools/convert_mdl.py models/ czde_dust.wad models.bin terror,leet,arctic,guerilla,militia && gzip -9 -k models.bin
python3 tools/pack_icons.py gfx/ czde_dust.wad icons.json
python3 tools/pack_sounds.py sound/ sounds.bin && gzip -9 -k sounds.bin
python3 tools/convert_turret.py Turret/ turret.bin && gzip -9 -k turret.bin
python3 tools/build.py src/game.template.html index.html 0.9 PACK=map.bin.gz MODELS=models.bin.gz ICONS=@icons.json SOUNDS=sounds.bin.gz TURRET=turret.bin.gz ROOMBA=roomba.bin.gz
```

Die BSP wird erst im Browser gelesen (Geometrie, Lightmaps, Kollision, Spawns, Bombsites). Weitere Maps sind damit später nur ein neues Datenpaket.

## Hinweis zu den Spieldateien

Map, Texturen, Himmel, Deko- und Spielermodelle sowie die Sounds stammen von Valve, der Geschützturm aus Portal (ebenfalls Valve) (Counter-Strike / Condition Zero) und stecken eingebettet in den gebauten HTML-Dateien. Gedacht für private Tests; die Rechte liegen bei Valve.
