# Kompass von <Name> — Hinweise für Agenten

Allgemeine Regeln: [METHODE.md](kern/METHODE.md) im eingebundenen kokompass (Submodul `kern/`).
Hier stehen nur die Abweichungen dieser Instanz.

1. Zuerst `kompass` ausführen. Nicht den ganzen Kompass einlesen, nur gezielt einzelne Knoten.
2. Vor jeder Bewertung eines Werkzeugs oder fremden Vorschlags: `kompass vorwissen "<Frage>"`.
3. Sitzungsende: `stand/aktuell.md` überschreiben, `log.md` ergänzen, `kompass sync && kompass pruefen`, eigene
   Dateien committen.

Für Projektarbeit `kompass repos` und gezielt `kompass kontext "<Thema>"` nutzen, danach im Zielrepo dessen
Anweisungen und Originalauftrag lesen. Quellenkonfiguration: `kontextquellen.md`, Sichtbarkeit: `repos.md`.
Ein Repo-Verweis oder eine Übergabe ist keine Arbeitsfreigabe. `kompass diagnose` prüft fehlende lokale Pfade.

## Abweichungen dieser Instanz

- (keine)
