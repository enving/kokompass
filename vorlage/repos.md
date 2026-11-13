# Repos: privat oder öffentlich

Repo-Navigation: `kompass repos` zeigt ausgewählte lokale Projekte, ihre Anweisungen und Übergaben.
Auswahl und Pfade werden in `kontextquellen.md` bzw. in vorhandenen Knoten mit `repo`-Feld gepflegt.
Hier bleibt die zuständige Sichtbarkeitsliste; die Projektbeschreibung wird nicht nochmals kopiert.

Bevor ein Agent in ein Repo schreibt, prüft er hier (oder direkt beim Anbieter, etwa `gh repo view <name> --json
visibility`), ob es öffentlich ist. Regel: METHODE.md Nr. 11 im eingebundenen kokompass.

| Repo | Sichtbarkeit | Was hinein darf | Was nie |
|---|---|---|---|
| (dieser Kompass) | privat | alles Persönliche außer `privat/` | Zugangsdaten |
| kokompass | öffentlich | Verallgemeinertes, erfundene Beispiele | Inhalte dieses Kompass |
