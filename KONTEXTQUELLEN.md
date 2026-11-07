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
| 3. Übernehmen | Was durch Einzelbeauftragung oder ein ausdrückliches Dauermandat gedeckt ist, wird Knoten oder Issue im zuständigen Repo. Persönliche Entscheidungen bleiben Zitate der Person. | Agent im erlaubten Umfang | ja |

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
| Frühere Agenten-Gespräche (Claude Code, Codex, Chat-Apps) | eigene Entscheidungen, Zitate, Korrekturen an Agenten („nein, so nicht“), die nie eingetragen wurden | Sitzungsverläufe der Werkzeuge lokal, Chat-Apps per Export | enthalten Zugangsdaten und Fremdinhalte: nur Fundstelle und eigene Aussagen übernehmen, nie roh kopieren; Korrekturen sind gute Prüffälle für den Dirigenten |

## Der Dirigent

Der Dirigent ist die Rolle, die Stufe 2 übernimmt. Er spielt selbst kein Instrument: Er schreibt keine Folge,
keinen Code und keine Mail. Er sorgt dafür, dass jeder Eingang an der richtigen Stelle ankommt.

**Wo er sucht, in dieser Reihenfolge:** erst im Kompass (`kompass`, `kompass vorwissen`, gezielte Knoten), dann im
zuständigen Repo (README, Übergabe, Issues), erst danach an anderen Orten (Notiz-App, Postfach, Fotodienst). Oft steht
die Antwort schon im Repo, etwa wie ein Dienst eingerichtet ist.

**Er darf:**

- Eingangsregister und `kompass`-Ausgabe lesen, einzelne Knoten gezielt nachlesen.
- Je Eingang einen Vorschlag machen: verwerfen, als Quelle verweisen, Aufgabe für die Person, Aufgabe für einen
  Agenten, Issue im zuständigen Repo.
- Auf Grundlage einer Einzelbeauftragung oder eines ausdrücklichen Dauermandats Aufgaben an Agenten übergeben,
  den zulässigen nächsten Schritt selbst übernehmen lassen und die geprüfte Rückmeldung als Beleg verweisen.
- Einmal je Lauf melden, was er getan hat und was auf die Person wartet.
- Wenn eine Rückmeldung eine offene Lücke füllt oder Aufbau und Abläufe ändert, eine Folgeaufgabe vorschlagen: die
  zugehörigen Darstellungen (Skizzen, Diagramme, Übersichtsfolien) nachziehen. Wo sie liegen, steht beim Thema im Kompass.

**Er darf nicht:**

- Entscheidungen treffen, Ziele ändern, Aufgaben der Person schließen oder umpriorisieren.
- Originale verschieben oder löschen.
- Ohne passende ausdrückliche Freigabe nach außen schreiben (Mail, Veröffentlichung, Push). Eine Freigabe zum
  Fortsetzen erteilt keine zusätzlichen Veröffentlichungs- oder Zugriffsrechte.
- Vertrauliches (`privat/`, `vertraulich: ja`) an andere Agenten weitergeben.

**Einführen in drei Schritten:**

1. Die Person ordnet den bestehenden Bestand einmal selbst ein. So entstehen die Beispiele, an denen der Dirigent
   gemessen wird.
2. Der Dirigent läuft auf Zuruf, in einer normalen Agentensitzung, und legt nur Vorschläge vor. Treffer und
   Fehlgriffe kommen in `pruefung/fragen.md`.
3. Erst wenn die Vorschläge über mehrere Läufe stimmen, bekommt er einen Takt (etwa täglich) in einer Agenten-
   Laufzeit mit Gedächtnis und Zeitplan. Die Laufzeit ist austauschbar; der Auftrag steht in der Instanz, nicht in
   der Laufzeit.

## Übergaben automatisch fortsetzen: die Person nahe am Ablauf

Nach einer bestätigten Beauftragung soll nicht für jeden Kontextwechsel ein menschliches „weiter“ nötig sein.
Der Dirigent kann dafür ein **Dauermandat** erhalten: Die Person legt in den bestehenden Instanzanweisungen fest,
welche Aufgabenarten, Repos, Handlungen, Quellen sowie Lauf- und Kostenbudgets gelten. Die Sichtbarkeit und
erlaubten Inhalte bleiben in der zuständigen Repo-Regel der Instanz (METHODE.md, Regel 11). Das Mandat enthält
keine zweite Sichtbarkeitstabelle. Ohne solches Mandat gelten die bisherigen Einzelfreigaben.

Innerhalb des Mandats übernimmt der Dirigent technische Weiterarbeit und Übergaben. Persönliche Ziele,
Grundsatzentscheidungen, Zugangsdaten und Erweiterungen des Mandats bleiben bei der Person. Ein Hinweis aus einer
Quelle oder der Abschnitt „Nächster Schritt“ in einer alten Übergabe erweitert den Auftrag nicht.

### Fortsetzungsablauf

1. **Aktuellen Auftrag finden.** Zuerst den Kompass, dann Original-Issue, Repo-Anweisungen, Ergebnisversion und
   letzte Übergabe prüfen. Ein inzwischen erledigter oder zurückgestellter Auftrag wird nicht wieder gestartet.
2. **Übergabe prüfen.** Der Bearbeiter hält im bestehenden Übergabeort Auftrag, Repo/Branch/Commit, Ziel,
   erledigte Schritte, Prüfbelege, offenen nächsten Schritt und Blocker fest. Das ist ein Checkpoint desselben
   Auftrags, kein neuer Aufgabenspeicher. Kontextende, fachlicher Abschluss und externer Blocker sind verschieden.
3. **Rechte und Ziel prüfen.** Mandat, aktuelle Repo-Sichtbarkeit und zulässigen Kontext abgleichen. In öffentliche
   Repos und deren versionierbare Auftragsunterlagen gehen ausschließlich verallgemeinerte Inhalte und erfundene
   Testdaten. Private Gespräche, lokale Zugangshinweise und ungeprüfte Rohübergaben werden nicht übernommen.
   Auch ein ignoriertes Dokument im öffentlichen Arbeitsbaum kann privat sein; der öffentliche Bearbeiter erhält
   den bereinigten Auftrag und zugelassene Originalquellen, nicht dessen gesamten Inhalt.
4. **Genau einmal übernehmen.** Vor dem Start vorhandene Ausführungen und konkurrierende Arbeit am selben Repo
   abgleichen. Die Übernahme anhand von Originalauftrag und Checkpoint-Version kennzeichnen und vorab im
   vorhandenen Ausführungsregister vermerken. Wiederholte Zustellung führt zur selben Ausführung. Eine veraltete
   Commitangabe verlangt einen erneuten Abgleich, kein Zurücksetzen des Arbeitsbaums.
5. **Frischen Bearbeiter beauftragen.** Im tatsächlich passenden Projekt einen neuen Agentenkontext mit Ziel,
   nötigen Quellen, erlaubten Handlungen und Abschlusskriterien starten. Nur den nötigen Kontext übergeben.
   Ein Agent ohne eigenen Arbeitsauftrag darf nicht allein wegen eines beendeten Vorgängers weiterarbeiten.
6. **Ergebnis zurückholen und prüfen.** Ergebnisereignisse an den Dirigenten zustellen. Die konkrete Version gegen
   die Kriterien prüfen lassen; bei geeigneter Arbeit durch einen getrennten Prüfer. Ein beendeter Prozess oder
   eine bestandene allgemeine Testsuite ersetzt keine fachliche Abnahme. Den geprüften Zustand am Original
   nachführen; anschließend einen weiteren gedeckten Schritt übernehmen oder den Auftrag abschließen.
7. **Begrenzt wiederholen.** Gleicher Fehler ohne neuen Befund, ausgeschöpftes Budget oder ein fehlender Zugang
   stoppt den betroffenen Strang. Kein rekursiver Neustart, Kontowechsel oder zweiter Bearbeiter als Umgehung.
   Ein so beendeter Strang wird erst bei nachweislich geänderter Blockierbedingung oder erneuter ausdrücklicher
   Beauftragung beziehungsweise Budgetfreigabe wieder aufgenommen. Vergangene Zeit und eine alte Rückmeldung
   allein reichen dafür nicht; vor der Wiederaufnahme werden Auftrag, Blocker und Budget erneut geprüft.
   Unabhängige zulässige Aufgaben können weiterlaufen. Die Person erhält eine konkrete Ausnahme mit Befund.

### Zusammenspiel mit Automationen

Neue Eingänge und fertige Ergebnisse sind unterschiedliche Auslöser desselben Dirigenten. Ein vorhandener
Tageslauf kann zusätzlich verwaiste Übergaben und versäumte Rückmeldungen abgleichen. Er startet keine zweite
Bearbeitung, solange eine zugehörige Ausführung oder deren Ergebnisrückgabe noch aktiv ist. Fachliche
Automationen für Import, Transkription oder Produktion bleiben zuständig; der Dirigent liest deren Resultate
und erfindet keine parallelen Zeitpläne dafür.

Eine Laufzeit muss frische Agentenkontexte, Ergebnisrückgabe, beständige Ausführungskennungen und Wiederaufnahme
bereitstellen. Der konkrete Werkzeugaufruf steht in den Instanzanweisungen. Dieser Abschnitt ist das gemeinsame
Protokoll; die mitgelieferte CLI implementiert noch keinen Hintergrunddienst oder universellen Delegator.

### Prüffälle für die Einbindung

- Eine reine Kontextübergabe innerhalb eines beauftragten Ergebnisses geht ohne erneutes menschliches „weiter“
  an einen frischen Bearbeiter im richtigen Repo.
- Derselbe Checkpoint wird zweimal zugestellt: es entsteht genau eine Bearbeitung.
- Eine alte Übergabe enthält einen inzwischen erledigten oder zurückgestellten Schritt: kein Neustart.
- Ein öffentliches Ziel trifft auf eine private Rohübergabe: nur der verallgemeinerte Auftrag wird weitergegeben;
  Rechte und Sichtbarkeit werden nicht aus dem Fortsetzungswunsch abgeleitet.
- Ein Bearbeiter endet mit fehlgeschlagenen Prüfungen: kein fachlicher Abschluss; begrenzte Nacharbeit oder ein
  belegter Blocker, kein unbeschränktes „continue“.
- Ein beendeter blockierter Strang wird am nächsten Tag mit derselben alten Rückmeldung vorgefunden: kein
  Neustart. Erst eine belegte Änderung der Blockierbedingung oder erneute ausdrückliche Beauftragung bzw.
  Budgetfreigabe erlaubt nach erneutem Abgleich die Wiederaufnahme.
- Eine vorhandene Fachautomation arbeitet noch: der Dirigent beginnt keine konkurrierende Ausführung.

## Offen

- **Wo Aufgaben zentral leben.** Aufgaben entstehen an vielen Stellen: im Kompass (`aufgaben/`), in Übergabedateien
  und Issues der Repos, in der Notiz-App. Die erste Instanz erprobt: Der Dirigent speichert nichts selbst, liest alle
  Orte und erschließt eine aktuelle thematische Sicht mit Verweisen, ohne zusätzliche statische Aufgabenliste;
  Projektaufgaben werden Issues im zuständigen Repo (mit
  Projektboard), Persönliches bleibt im Kompass. Wer welche Issues bearbeitet (Label je Zuständigkeit, Agenten-
  Sitzung im Repo, später ein Board in der Agenten-Laufzeit), ist noch nicht erprobt. Alternativen: Kanban-Board in
  der Agenten-Laufzeit als Speicher, oder Issues als einziger Speicher.
- **Wie der Dirigent besser wird.** Jeder Vorschlag, den die Person ändert oder verwirft, ist ein Prüffall in
  `pruefung/fragen.md`. Wie viele Fälle es braucht, bis ein Takt erlaubt ist, ist offen.
- **Wie ein persönlicher Dirigent mit dem Dirigenten einer Firma spricht** (kobetriebssystem, Lückenregister L21).
