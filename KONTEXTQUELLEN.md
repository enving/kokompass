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

## Laufzeit der eigenen Instanz

Die gemeinsamen Werkzeuge lesen Instanzwerte aus der Frontmatter von `kontextquellen.md`.
Eine leere Vorlage konfiguriert keine externen Quellen. Ein Pfad ist ein Zugangshinweis, keine Freigabe
zum Lesen aller Inhalte oder zur Bearbeitung von Aufgaben. Relative Pfade beziehen sich auf die Instanz;
`~` bezeichnet das eigene Benutzerverzeichnis. `KOMPASS_DIR` wählt die Instanz, `KOMPASS_VAULT` kann
deren Vault-Pfad für einen einzelnen Aufruf überschreiben.

| Feld | Verwendung |
|---|---|
| `vault_pfad` | Optionaler Obsidian-Vault für Eingang, Wiki-Pflege und Export |
| `repo_wurzeln` | Liste ausgewählter Ordner, deren direkte Git-Repos erfasst werden |
| `repo_pfade` | Zusätzliche einzelne Repo-Pfade, auch für eine Meldung fehlender Arbeitsbäume |
| `eingang_movies`, `eingang_downloads`, `eingang_zulieferer` | Optionale Ordner für direkte Dateierfassung |
| `studio_wurzel` | Optionaler Projektbereich für Aufnahme-/Deck-Dateien |
| `spiegel_ordner`, `spiegel_sperre` | Explizite Ordnerauswahl und Inhaltssperren für den gesonderten Spiegelaufruf |
| `github_aktiv` | `ja` aktiviert den lesenden GitHub-Abgleich bei Kontext- und Gesamtabfragen |
| `github_workflow_repos`, `github_fehler_conclusions` | Auswahl einzelner Workflow-Ereignisse und Fehlerzustände |
| `github_speicher_grenze_bytes` | Zum eigenen Tarif passende Schwelle der Speicherwarnung |
| `immich_url` | Optionaler lokaler Gesundheitsendpunkt; kein Medienimport |
| `notebook_id` | Ausgewähltes Notebook für den Vergleich eines autorisiert gelieferten Inventars |
| `projekt_aliases` | Liste `Präfix=Projekt` zur Gruppierung vorhandener Registereinträge |
| `privates_git_repo` | Erlaubtes `Konto/Repo` des optionalen privaten Push-Schutzes; ohne Angabe gesperrt |
| `regeln_datei` | Zuständige Sichtbarkeitsliste für deren ausdrücklich aufgerufene GitHub-Aktualisierung |
| `stand_datei` | Ziel für `kompass datei`, wenn der Aufruf keinen Pfad angibt |
| `okf_pruefer` | Optionaler installierter OKF-Prüfer für `kompass validieren` |
| `stt_api_pfad` | Optionaler vorhandener lokaler Spracherkennungsadapter |
| `output_ziel` | Optionaler ausdrücklich gesetzter Bezugspunkt für den Output-Bericht |

Wiki-/Medienverarbeitung hat ihre bestehende Konfiguration in `werkzeuge/wiki-pflege.json`;
eine unbefüllte Instanz verwendet die mitgelieferte Vorlage. Dort stehen Modellwahl, ausgeschaltete
Cloudnutzung, Laufbudgets und bei Bedarf `python_stt`, `python_docling`, `doc2md`, `doc2md_health`,
`voxtral_skript`, `ffmpeg` und `ffprobe`. Schlüssel werden ausschließlich über die Umgebung der
bereits eingerichteten Werkzeuge bereitgestellt. Fehlende externe Installationen werden gemeldet.
Kokompass installiert sie nicht und erzeugt keinen kostenpflichtigen Modelltest.

`kompass repos` zeigt vorhandene Verweise samt Projekt-Anweisungen und Übergaben. Beschreibungen
kommen aus den vorhandenen Knoten mit lokalem `repo`-Feld; sie werden nicht in einer zweiten Liste gepflegt.
`kompass diagnose` prüft die lokale Einrichtung lesend. Host-Zeitpläne, Logins und tatsächliche Modellqualität
sind dadurch nicht geprüft.

Das maßgebliche Fortsetzungsregister bleibt `.zustand/eingaenge.json`. Ein frischer Scan erzeugt es pausiert.
`db-import` spiegelt es nur nach SQLite, `weiter` liest die JSON direkt. Git enthält diesen lokalen Zustand
nicht: Er braucht eine eigene Sicherung außerhalb der Instanz. Nach Wiederherstellung Originalaufträge,
aktive Bearbeiter und Checkpoints abgleichen, bevor die Pause aufgehoben wird. Eine Repo-Erfassung oder ein
erreichbarer Dienst ersetzt diesen Abgleich nicht. Die Host-Anbindung richtet die Person ausdrücklich ein;
die gemeinsamen Werkzeuge legen keinen Zeitplan an.

## Beispiele für Quellen

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

## Lernschleife: der Dirigent wird mit jedem Lauf besser

Der Dirigent lernt nicht, indem ein Modell sich ändert, sondern indem **Auftrag, Regel und Prüffälle besser werden**.
Das geschieht in jedem Lauf nach demselben kleinen Ablauf, damit es nicht vom Zufall oder von der Erinnerung eines
Agenten abhängt. Die Person behält die Hoheit: Verbessert wird das Verfahren, nie Ziele, Befugnisse, Budgets oder
Sichtbarkeit.

1. **Beobachten.** Am Ende jedes Laufs hält der Dirigent höchstens drei Beobachtungen fest, jeweils mit Fundstelle,
   nie als Rohtext: ein eigener Fehler, eine Korrektur der Person, ein Blocker, ein beinahe doppelter Start, eine
   überholte Übergabe, ein Schritt, der unnötig lange gedauert hat. Ein Lauf ohne Beobachtung schreibt „keine“ und
   sagt, was er dafür geprüft hat.
2. **Einordnen.** Zu jeder Beobachtung die zuständige vorhandene Regel finden (Instanzauftrag, Skill, diese Methode).
   Passt keine, ist das eine belegte Lücke. Eine neue Regel an einer zweiten Stelle entsteht nie; es wird die
   zuständige Quelle ergänzt, abhängige Anweisungen verweisen darauf.
3. **Eine Verbesserung je Lauf.** Die kleinste Änderung an der zuständigen Quelle, die die Beobachtung behebt. Mehrere
   Beobachtungen ergeben mehrere Vorschläge, aber höchstens eine umgesetzte Änderung je Lauf; die übrigen bleiben als
   offener Prüfpunkt stehen. So bleibt eine Regression einer Änderung zuordenbar.
4. **Prüffall dazu.** Jede Änderung bekommt einen wiederholbaren Prüffall: Ausgangslage, erwartetes Verhalten, woran
   man es erkennt. Beispiel (erfunden): Eine Übergabe nennt einen Schritt als offen, das zugehörige Issue ist
   geschlossen; erwartet wird kein Neustart und ein vermerkter Widerspruch.
5. **Im nächsten Lauf nachprüfen.** Der nächste Lauf prüft die Prüffälle der letzten Änderungen gegen sich selbst.
   Kehrt der Fehler trotz Änderung wieder, war die Ursache falsch eingeordnet. Entsteht ein neuer Fehler, wird die
   Änderung zurückgenommen und als Befund festgehalten. Technische Verbesserungen werden so bei Regression revertiert.
6. **Verallgemeinern.** Hat sich eine Änderung über mehrere Läufe ohne Regression bewährt, ist sie ein Kandidat für
   die Vorlage ([BEITRAGEN.md](BEITRAGEN.md)): verallgemeinert, ohne Einzelfall, und nur mit Ja der Person.

Wo die Beobachtungen und Prüffälle liegen, legt die Instanz in ihrem Dirigentenauftrag fest; die Methode verlangt dafür
keine zusätzliche Datei und keinen zweiten Aufgabenspeicher. Ein bestehender Laufbericht oder ein Fragenregister
genügt, solange Beobachtung, Änderung, Prüffall und Nachprüfung dort zusammenfinden.

### Prüffälle für die Lernschleife

- Ein Lauf endet ohne Beobachtung und ohne Vermerk, was geprüft wurde: unvollständig.
- Zwei Beobachtungen ergeben zwei Änderungen im selben Lauf: nur eine wird umgesetzt, die andere bleibt Vorschlag.
- Eine Änderung führt zu einem neuen Fehler: sie wird zurückgenommen, nicht durch eine weitere Regel überdeckt.
- Eine Beobachtung verlangt mehr Befugnisse oder ein größeres Budget: das ist ein Vorschlag an die Person, keine
  Änderung des Dirigenten.
- Dieselbe Regel steht nach der Änderung an zwei Stellen: die Kopie wird entfernt und durch einen Verweis ersetzt.

## Offen

- **Wo Aufgaben zentral leben.** Aufgaben entstehen an vielen Stellen: im Kompass (`aufgaben/`), in Übergabedateien
  und Issues der Repos, in der Notiz-App. Die erste Instanz erprobt: Der Dirigent speichert nichts selbst, liest alle
  Orte und erschließt eine aktuelle thematische Sicht mit Verweisen, ohne zusätzliche statische Aufgabenliste;
  Projektaufgaben werden Issues im zuständigen Repo (mit
  Projektboard), Persönliches bleibt im Kompass. Wer welche Issues bearbeitet (Label je Zuständigkeit, Agenten-
  Sitzung im Repo, später ein Board in der Agenten-Laufzeit), ist noch nicht erprobt. Alternativen: Kanban-Board in
  der Agenten-Laufzeit als Speicher, oder Issues als einziger Speicher.
- **Wie viele Läufe eine Änderung bestehen muss.** Der Ablauf steht oben (Lernschleife). Jeder Vorschlag, den die
  Person ändert oder verwirft, ist zusätzlich ein Prüffall in `pruefung/fragen.md`. Offen ist, nach wie vielen
  Läufen ohne Regression eine Änderung als bewährt gilt und zur Vorlage hochgeht.
- **Wie ein persönlicher Dirigent mit dem Dirigenten einer Firma spricht** (kobetriebssystem, Lückenregister L21).
