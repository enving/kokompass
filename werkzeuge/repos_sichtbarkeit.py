#!/usr/bin/env python3
"""Schreibt die Tabelle „Alle Repos“ in rules.md neu aus GitHub (gh repo list).

Aufruf: python3 werkzeuge/repos_sichtbarkeit.py [--besitzer <Konto>]
Nur der Bereich zwischen <!-- repos:start --> und <!-- repos:ende --> wird ersetzt. Hinweise in der dritten Spalte
bleiben erhalten, solange das Repo noch existiert. Zuständige Quelle für die Sichtbarkeit bleibt GitHub.
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

from konfiguration import wurzel, felder, pfad

REGELN = pfad(felder().get("regeln_datei", "repos.md"))
START, ENDE = "<!-- repos:start -->", "<!-- repos:ende -->"


def main(argv):
    besitzer = argv[argv.index("--besitzer") + 1] if "--besitzer" in argv else json.loads(subprocess.run(["gh", "api", "user"], capture_output=True, text=True, check=True).stdout)["login"]
    roh = subprocess.run(["gh", "repo", "list", besitzer, "--limit", "500", "--json",
                          "name,visibility,isFork,isArchived"], capture_output=True, text=True, check=True).stdout
    repos = json.loads(roh)
    text = REGELN.read_text(encoding="utf-8")
    alt = text[text.index(START):text.index(ENDE)]
    hinweise = dict(re.findall(r"^\| [^|]+ \| `([^`]+)` \| (.*?) \|$", alt, re.M))
    zeilen = [START, "", f"Abzug {datetime.date.today()}: {len(repos)} Repos, "
              f"{sum(r['visibility'] == 'PUBLIC' for r in repos)} öffentlich.", "",
              "| Sichtbarkeit | Repo | Hinweis |", "|---|---|---|"]
    for r in sorted(repos, key=lambda r: (r["visibility"] != "PUBLIC", r["name"].lower())):
        merk = [m for m, an in (("Fork", r["isFork"]), ("archiviert", r["isArchived"])) if an]
        alt_hinweis = hinweise.get(r["name"], "").strip()
        for m in merk:
            alt_hinweis = alt_hinweis.replace(m, "").strip(", ")
        hinweis = ", ".join(merk + ([alt_hinweis] if alt_hinweis else []))
        sicht = "**öffentlich**" if r["visibility"] == "PUBLIC" else "privat"
        zeilen.append(f"| {sicht} | `{r['name']}` | {hinweis} |")
    zeilen += ["", ""]
    REGELN.write_text(text.replace(alt, "\n".join(zeilen)), encoding="utf-8")
    print(f"rules.md: {len(repos)} Repos geschrieben")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
