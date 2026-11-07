# Beitragen: vom eigenen Kompass zurück in die Vorlage

Jeder Kompass ist privat. Was sich darin bewährt, soll trotzdem allen helfen. Dafür gibt es zwei Ziele:

| Was | Wohin |
|---|---|
| Methode, Vorlage, Werkzeug (`kompass`), Prüfungen | dieses Repo, **kokompass** |
| Regeln, Skills, Wissen einer Firma | das Betriebssystem der Firma, etwa [kobetriebssystem](https://github.com/enving/kobetriebssystem) |

## Der Weg

1. **Bemerken.** Der Agent sieht ein Muster: eine Korrektur, die dreimal kam, eine Regel, die fehlt, ein Werkzeug,
   das sich bewährt. Er trägt es in `beitraege.md` der eigenen Instanz ein, mit Beleg, der dort bleibt.
2. **Verallgemeinern.** Ohne Personen-, Kunden- und Gesundheitsdaten, ohne Namen und Einzelfall, sodass es für jede
   Person gilt und nicht für diese eine.
3. **Vorlegen.** Die Person sagt Ja, Nein oder „nur bei mir“. Ohne Ja geht nichts hoch. Die Person kann ein **Dauer-Ja
   mit Rhythmus** geben (zum Beispiel einmal pro Woche): Der Dirigent sammelt dann in diesem Takt alle bewährten
   Verbesserungen der Instanz, verallgemeinert sie (Schritt 2) und prüft sie (Schritt 4). Das Dauer-Ja ersetzt weder die
   Verallgemeinerung noch die Prüfung; was nicht verallgemeinerbar ist, bleibt in der Instanz. Der Rhythmus steht im
   Dirigentenauftrag der Instanz, nicht in einem zusätzlichen Zeitplan.
4. **Prüfen.** Vor dem Push: `python3 -m unittest discover tests` und eine Suche nach privaten Begriffen der
   eigenen Instanz (Namen aus `person/`, Netzwerk, Auftraggeber, eigene Pfade) gegen den Diff. Erwartet: 0 Treffer.
   Die CI prüft zusätzlich mit gitleaks.
5. **PR.** Werkzeugänderungen kommen mit Test gegen `beispiel/`. Neue Regeln gehen nach [METHODE.md](METHODE.md),
   nicht in eine zweite Datei.
6. **Zurück.** Nach dem Merge holt die eigene Instanz die neue Fassung über das Submodul
   (`git submodule update --remote kern`) und setzt den Eintrag in `beitraege.md` auf „übernommen“.

## Was nie hochgeht

Ziele, Grenzen, Gesundheit, Familie, Geld, Bewerbungen, Rohgespräche, alles unter `privat/` und alles mit
`vertraulich: ja`. Testdaten sind erfunden, nie aus einer echten Instanz kopiert.

## Arbeiten im Submodul

Wer in seiner Instanz unter `kern/` eine Verbesserung baut, arbeitet dort auf einem eigenen Zweig und stellt den PR
von dort. Die Instanz zeigt danach auf den Commit nach dem Merge, nicht auf den Arbeitszweig.
