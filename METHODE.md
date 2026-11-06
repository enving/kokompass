# Methode

Diese Datei ist die zuständige Quelle für die allgemeinen Regeln eines Kompass. Eine Instanz (dein eigener
Kompass) beschreibt in ihrer `AGENTS.md` nur ihre Abweichungen und verweist für alles andere hierher.

## Wofür ein Kompass da ist

Ein Kompass ist das Gedächtnis einer Person für ihre Agenten: wer sie ist, was sie will, was sie entschieden hat,
was offen ist. Er gehört der Person und darf unordentlich sein. Menschen verfolgen mehrere Ziele gleichzeitig, auch
wenn sie sich reiben. Das ist kein Fehler, den ein Agent beheben muss.

Er ist kein Projektarchiv. Hat ein Thema ein eigenes Repo, gehören Doku, Fragen und Aufgaben dorthin (Datei, Issue,
PR). Im Kompass bleiben der Verweis, die Zitate der Person und ihre Entscheidungen.

## Knoten

Jede Datei ist ein Knoten: Markdown mit YAML-Frontmatter im Format
[OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md). Pflicht in jedem Knoten: `type`, `title`,
`description`, `timestamp`. Beziehungen stehen als Listen bundle-absoluter Pfade im Frontmatter, etwa
`betrifft: [/ideen/beispiel.md]`. Der Abschnitt zwischen `<!-- verbindungen:start -->` und
`<!-- verbindungen:ende -->` wird von `kompass sync` erzeugt und nie von Hand bearbeitet.

| Ordner | `type` | Wofür | Zusätzliche Pflichtfelder |
|---|---|---|---|
| `person/` | `Person`, `Ziel` | Wer die Person ist, was sie will | `name` (in `ich.md`), `stand` (in `ziele.md`) |
| `entscheidungen/` | `Entscheidung` | Was die Person entschieden hat | `entschieden_von`, `datum`; Zitat mit Datum im Text |
| `einschaetzungen/` | `Einschaetzung` | Bewertung, Empfehlung, Entwurf eines Agenten | `modell`, `datum` |
| `belege/` | `Beleg` | Was nachweislich existiert oder geschah | Fundstelle im Text |
| `aufgaben/` | `Aufgabe` | Nächster Schritt | `wer` (Person oder `Agent`), `status`, `prioritaet`, optional `frist` |
| `fragen/` | `Frage` | Offene Frage | `status`, `prioritaet` |
| `ideen/` | `Idee` | Idee oder fremder Vorschlag | `status`; `antrieb` setzt nur die Person |
| `quellen/` | `Quelle` | Artikel, Video, Dokument | `status`, `ausgewertet_von`; Abschnitt `# Citations` |
| `gespraeche/` | `Gespraech` | Was gesagt wurde | `datum` |
| `stand/aktuell.md` | `Stand` | „Hier weitermachen“ für die nächste Sitzung | `stand` |
| `pruefung/fragen.md` | `Pruefung` | Kontext-Test und Aufgabenliste (siehe unten) | – |

Weitere Ordner sind erlaubt (etwa `netzwerk/`, `stationen/`, `aussendungen/`). `kompass pruefen` verlangt nur
`type` und auflösbare Verweise.

## Regeln für Agenten

1. **Entscheiden tut nur die Person.** Kein Knoten in `entscheidungen/` ohne ihr Wort, als Zitat mit Datum.
2. **Beleg, Einschätzung und Entscheidung bleiben getrennt.** Eigene Einschätzungen tragen Modell und Datum und
   werden nie als Tatsache formuliert. Behauptungen über Märkte oder Werkzeuge brauchen eine Quelle von außen,
   sonst sind sie als Annahme markiert.
3. **Richtung nie aus Belegen ableiten.** Belege zeigen Können, nicht Willen. Was jemand gut kann, ist nicht, was
   er will.
4. **Mehrere Ziele gelten parallel.** Spannungen benennen, nicht auflösen. Eine Zielliste ist keine Rangfolge.
5. **Frust, Zweifel und Kehrtwenden als Zitat festhalten,** nicht als neues Ziel.
6. **Fragen an die Person stehen ganz oben im Knoten** unter `# An <Name>`, nummeriert. `kompass` listet die
   Fundstellen beim Start.
7. **Aus einer beiläufigen Erwähnung keinen Knoten bauen,** erst bestätigen lassen.
8. **Vor jeder Bewertung** eines Werkzeugs, Anbieters oder fremden Vorschlags `kompass vorwissen "<Frage>"`
   ausführen. Frühere Einschätzungen sind Gedächtnis, nicht Urteil.
9. **Am Sitzungsende** `stand/aktuell.md` („Hier weitermachen“) überschreiben, den Verlauf in `log.md` ergänzen,
   `kompass sync` und `kompass pruefen` laufen lassen, die eigenen Dateien committen.
10. **Nichts Vertrauliches nach außen.** Was unter `privat/` liegt oder `vertraulich: ja` trägt, liest kein Agent
    außerhalb der Person und es geht in keinen Beitrag.

## Prüfen, ob der Kompass trägt

Ein Kompass ist nur so gut, wie seine Agenten ihn nutzen. Darum hat jede Instanz `pruefung/fragen.md` mit zwei
Listen (nach Cole Medins „4 C“, siehe [README](README.md#herkunft)):

- **Kontext-Test:** Eine frische Sitzung beantwortet ohne Suche, wer die Person ist, woran sie arbeitet und mit
  wem. Kann sie das nicht, fehlt etwas in `person/` oder in der Startausgabe.
- **Aufgabenliste:** Feste, wiederkehrende Aufgaben, die nach jeder größeren Änderung (Modellwechsel, neue Regel,
  neues Werkzeug) laufen. Wird ein Ergebnis schlechter, wird die Änderung zurückgenommen oder nachgebessert.

Automatische Läufe kommen erst, wenn eine Aufgabe von Hand verlässlich klappt, und jeder Lauf meldet, was er getan
hat.

## Kontextquellen und Dirigent

Wie Notizen, Fotos, Memos und andere Quellen in den Kompass kommen und wer sie einordnet, steht in
[KONTEXTQUELLEN.md](KONTEXTQUELLEN.md). Kurz: Erfassen schreibt nur ins Register, Einordnen macht Vorschläge,
übernommen wird erst nach Ja der Person.
