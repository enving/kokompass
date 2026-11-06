# Kontextquellen anbinden und der Dirigent

Ein Kompass weiß nur, was in ihn hineinkommt. Der Alltag einer Person liegt aber verstreut: Notizen, Mails,
Kalender, Fotos und Bildschirmfotos, Sprachmemos, Browser-Ausschnitte, Repos. Diese Anleitung beschreibt, wie man
solche Quellen anbindet, ohne den Kompass zu fluten oder Privates zu verlieren, und welche Rolle das Einordnen
übernimmt: den **Dirigenten**.

## Grundsatz: Eingang ist nicht Einarbeitung

Jede Quelle durchläuft drei Stufen. Nur die letzte schreibt Knoten.

| Stufe | Was passiert | Wer | Schreibt in den Kompass? |
|---|---|---|---|
| 1. Erfassen | Neue Einträge seit dem letzten Lauf auflisten: Datum, Art, Fundstelle, Prüfsumme. Kein Lesen, kein Modell. | Skript | nein, nur ins Eingangsregister |
| 2. Einordnen | Je Eintrag: verwerfen, als Quelle verweisen, Aufgabe vorschlagen, an ein Repo oder einen Agenten delegieren. | Dirigent, anfangs die Person selbst | nein, nur Vorschläge |
| 3. Übernehmen | Was die Person bestätigt, wird Knoten (Quelle, Aufgabe, Entscheidung als Zitat) oder Issue im zuständigen Repo. | Agent nach Ja | ja |

Erst wenn Stufe 2 von Hand verlässlich klappt, wird sie automatisiert (METHODE.md, „Prüfen, ob der Kompass trägt“).

## Regeln für jede Quelle

1. **Zeitfenster statt Vollbestand.** Nur die letzten Wochen, etwa die letzten zwei Monate. Ältere Einträge nur auf
   ausdrücklichen Wunsch. Das hält den Eingang klein und aktuell.
2. **Verweis statt Kopie.** Originale bleiben in der Quelle (Fotodienst, Notiz-App, Postfach). Der Kompass speichert
   Fundstelle, Datum und eine Zeile Inhalt, keine Bilder und keine Volltexte von Mails.
3. **Auswahl vor Menge.** Je Quelle ist festgelegt, welche Art zählt, etwa nur Bildschirmfotos und keine
   Familienfotos, nur markierte Mails, nur ein Notizordner „Eingang“.
4. **Lokal zuerst.** Texterkennung, Transkription und Zusammenfassung laufen möglichst auf dem eigenen Gerät. Geht
   etwas an ein Cloud-Modell, steht das im Register.
5. **Zugangsdaten nie im Kompass.** Schlüssel liegen im Schlüsselbund oder in einer Datei außerhalb des Repos; das
   Register nennt nur, wo.
6. **Jede Quelle steht im Register** (`kontextquellen.md` der Instanz): was, wie erreichbar, welches Zeitfenster,
   welche Auswahl, wer einordnet, letzter Lauf. Eine Quelle ohne Eintrag ist nicht angebunden.

## Typische Quellen

| Quelle | Gute Auswahl | Erfassen über | Vorsicht |
|---|---|---|---|
| Notizen (Obsidian, Notion) | Ordner „Eingang“, Clippings, Tagesnotizen | Dateien mit Änderungsdatum | Notiz-App nicht als zweiten Kompass führen |
| Fotos (Immich, Apple Fotos) | Bildschirmfotos, Whiteboards, Belege der letzten Wochen | API oder Export der Metadaten; Texterkennung lokal | Familien- und Gesundheitsbilder nie, Gesichter nie |
| Sprachmemos | neue Aufnahmen | lokale Transkription | Gespräche mit Dritten nur mit deren Zustimmung |
| Mail | markierte oder an sich selbst geschickte Mails | lokale Suche oder Export | nie den ganzen Posteingang |
| Kalender | Termine der nächsten zwei Wochen | Export oder Konnektor | nur lesen |
| Browser | Lesezeichen, Ausschnitte | Clipper in die Notiz-App | keine Verlaufsüberwachung |
| Repos, Issues | eigene offene Issues, Erwähnungen | `gh` | Doku bleibt im Repo, im Kompass nur Verweis |

## Der Dirigent

Der Dirigent ist die Rolle, die Stufe 2 übernimmt. Er spielt selbst kein Instrument: Er schreibt keine Folge,
keinen Code und keine Mail. Er sorgt dafür, dass jeder Eingang an der richtigen Stelle ankommt.

**Er darf:**

- Eingangsregister und `kompass`-Ausgabe lesen, einzelne Knoten gezielt nachlesen.
- Je Eingang einen Vorschlag machen: verwerfen, als Quelle verweisen, Aufgabe für die Person, Aufgabe für einen
  Agenten, Issue im zuständigen Repo.
- Nach Ja der Person Aufgaben an Agenten übergeben und deren Rückmeldung als Beleg verweisen.
- Einmal je Lauf melden, was er getan hat und was auf die Person wartet.

**Er darf nicht:**

- Entscheidungen treffen, Ziele ändern, Aufgaben der Person schließen oder umpriorisieren.
- Originale verschieben oder löschen.
- Ohne Ja nach außen schreiben (Mail, Veröffentlichung, Push).
- Vertrauliches (`privat/`, `vertraulich: ja`) an andere Agenten weitergeben.

**Einführen in drei Schritten:**

1. Die Person ordnet den bestehenden Bestand einmal selbst ein. So entstehen die Beispiele, an denen der Dirigent
   gemessen wird.
2. Der Dirigent läuft auf Zuruf, in einer normalen Agentensitzung, und legt nur Vorschläge vor. Treffer und
   Fehlgriffe kommen in `pruefung/fragen.md`.
3. Erst wenn die Vorschläge über mehrere Läufe stimmen, bekommt er einen Takt (etwa täglich) in einer Agenten-
   Laufzeit mit Gedächtnis und Zeitplan. Die Laufzeit ist austauschbar; der Auftrag steht in der Instanz, nicht in
   der Laufzeit.

## Offen

- **Wo Aufgaben zentral leben.** Aufgaben entstehen an vielen Stellen: im Kompass (`aufgaben/`), in Übergabedateien
  und Issues der Repos, in der Notiz-App. Der Dirigent sieht sie nur, wenn sie als Eingang erfasst werden. Drei Wege
  sind denkbar: ein Kanban-Board in der Agenten-Laufzeit, Issues mit einem Projektboard über alle Repos als einziger
  Speicher, oder der Dirigent speichert nichts selbst, liest alle Orte und führt nur eine Tagesliste mit Verweisen.
  Der dritte Weg legt keinen neuen Speicher an; persönliche Aufgaben bleiben dann im Kompass, Projektaufgaben im
  Repo. Noch nicht erprobt.
- **Wie der Dirigent besser wird.** Jeder Vorschlag, den die Person ändert oder verwirft, ist ein Prüffall in
  `pruefung/fragen.md`. Wie viele Fälle es braucht, bis ein Takt erlaubt ist, ist offen.
- **Wie ein persönlicher Dirigent mit dem Dirigenten einer Firma spricht** (kobetriebssystem, Lückenregister L21).
