# Repos: privat oder öffentlich

Bevor ein Agent in ein Repo schreibt, prüft er hier (oder direkt beim Anbieter, etwa `gh repo view <name> --json
visibility`), ob es öffentlich ist. Regel: METHODE.md Nr. 11 im eingebundenen kokompass.

| Repo | Sichtbarkeit | Was hinein darf | Was nie |
|---|---|---|---|
| (dieser Kompass) | privat | alles Persönliche außer `privat/` | Zugangsdaten |
| kokompass | öffentlich | Verallgemeinertes, erfundene Beispiele | Inhalte dieses Kompass |
