#!/usr/bin/env python3
"""Betriebsdatenbank des Dirigenten: abfragbarer Spiegel von `.zustand/eingaenge.json`.

Nur ZUSTAND (Eingänge, Übergaben, Fortsetzungen, Steuerung, Ereignisse, Beobachtungen). Wissen bleibt
Markdown/OKF. Die JSON-Datei bleibt maßgeblich und wird nie verändert; `db-import` baut den Spiegel in
einer Transaktion vollständig neu auf (idempotent, gelöschte Schlüssel verschwinden). Die Datenbank liegt
unter `.zustand/` und ist wie das Register gitignoriert. Keine Abhängigkeit außer der Standardbibliothek.

Befehle:  kompass db-import   Register -> Datenbank
          kompass wartet      Block „Wartet auf dich“ aus der Datenbank (nach Repo/Projekt gegliedert)
          kompass weiter      Bereite Fortsetzungen direkt aus dem Register; --abschluss prüft Leerlauf
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from datetime import datetime

from konfiguration import wurzel, felder

INSTANZ = wurzel()
REGISTER = ".zustand/eingaenge.json"
DATENBANK = ".zustand/dirigent.sqlite"

# Migrationen: Index + 1 = Version (PRAGMA user_version). Nur anhängen, bestehende nie ändern.
MIGRATIONEN = (
    """
    CREATE TABLE eingaenge (
        schluessel TEXT PRIMARY KEY, art TEXT, pfad TEXT, status TEXT, version TEXT,
        erstmals TEXT, gesehen TEXT, daten TEXT NOT NULL);
    CREATE TABLE repos (
        pfad TEXT PRIMARY KEY, head TEXT, datum TEXT, pruefbedarf TEXT, daten TEXT NOT NULL);
    CREATE TABLE fortsetzungen (
        schluessel TEXT PRIMARY KEY, projekt TEXT NOT NULL, status TEXT, typ TEXT, wartet_auf TEXT,
        frage TEXT, antwort_genuegt TEXT, danach TEXT, seit TEXT, wiederaufnahme TEXT,
        daten TEXT NOT NULL);
    CREATE INDEX fortsetzungen_projekt ON fortsetzungen(projekt);
    CREATE TABLE steuerung (schluessel TEXT PRIMARY KEY, daten TEXT NOT NULL);
    CREATE TABLE ereignisse (schluessel TEXT PRIMARY KEY, daten TEXT NOT NULL);
    CREATE TABLE beobachtungen (
        id INTEGER PRIMARY KEY AUTOINCREMENT, datum TEXT NOT NULL, text TEXT NOT NULL,
        pruefstand TEXT, quelle TEXT);
    CREATE TABLE meta (schluessel TEXT PRIMARY KEY, wert TEXT);
    """,
    """
    ALTER TABLE beobachtungen ADD COLUMN register_schluessel TEXT;
    CREATE UNIQUE INDEX beobachtungen_register ON beobachtungen(register_schluessel);
    ALTER TABLE fortsetzungen ADD COLUMN knotenpfad TEXT;
    """,
)

# Schlüsselpräfix -> Repo/Projekt. Reihenfolge egal; Treffer per Anfang des Präfix. Unbekanntes Präfix
# erscheint unter seinem eigenen Namen, nichts wird verschluckt. Bei `wartet:<thema>` zählt das Thema.
PROJEKT_VON_PRAEFIX = dict(x.split("=", 1) for x in felder().get("projekt_aliases", []) if "=" in x)

SAMMEL_PRAEFIX = "wartet"

# Status, bei denen die Frage entschieden oder erledigt ist: kein „wartet“ mehr.
ERLEDIGT = re.compile(r"erledigt|abgenommen|^dirigent_entschieden$|^verworfen$|^beantwortet$")
KURZ = 130


def projekt_von(schluessel):
    """Repo/Projekt aus dem Schlüsselpräfix (`koprotokoll:37:ab`, `wartet:deck-studio-offen`)."""
    teile = str(schluessel).split(":")
    erst = teile[0]
    if erst == SAMMEL_PRAEFIX and len(teile) > 1:
        thema = teile[1]
        for praefix in sorted(PROJEKT_VON_PRAEFIX, key=len, reverse=True):
            if thema == praefix or thema.startswith(praefix + "-"):
                return PROJEKT_VON_PRAEFIX[praefix]
        return thema.split("-")[0]
    return PROJEKT_VON_PRAEFIX.get(erst, erst)


def verbinden(pfad):
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(pfad)
    migrieren(conn)
    return conn


def version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrieren(conn):
    aktuell = version(conn)
    if aktuell > len(MIGRATIONEN):
        raise RuntimeError(f"Datenbank neuer als dieses Werkzeug (Version {aktuell})")
    for nr in range(aktuell, len(MIGRATIONEN)):
        with conn:
            conn.executescript("BEGIN;" + MIGRATIONEN[nr])
            conn.execute(f"PRAGMA user_version = {nr + 1}")


def _text(wert):
    """Spalten sind Text; Verschachteltes wird als JSON abgelegt, nichts geht verloren (`daten`)."""
    if wert is None or isinstance(wert, str):
        return wert
    return json.dumps(wert, ensure_ascii=False, sort_keys=True)


def _json(wert):
    return json.dumps(wert, ensure_ascii=False, sort_keys=True)


def register_laden(register):
    daten = json.loads(Path(register).read_text(encoding="utf-8"))
    if not isinstance(daten, dict):
        raise ValueError("Register ist kein JSON-Objekt")
    return daten


def register_beobachtungen(reg):
    """Explizite Einträge aus demselben JSON, keine Ableitung aus Freitext/Graph.

    `beobachtungen` ist ein optionales Objekt Kennung -> {datum, text, quelle, pruefstand}.
    Eine Fortsetzung darf alternativ ihren strukturierten `lerneintrag` mit diesen Feldern tragen.
    Der JSON-Pointer bleibt als Herkunft erhalten; unvollständige Einträge brechen den Import ab.
    """
    def pointer(key):
        return str(key).replace("~", "~0").replace("/", "~1")

    eintraege = reg.get("beobachtungen") or {}
    if not isinstance(eintraege, dict):
        raise ValueError("beobachtungen muss ein Objekt mit stabilen Kennungen sein")
    kandidaten = [("/beobachtungen/" + pointer(k), v) for k, v in eintraege.items()]
    kandidaten += [("/fortsetzungen/" + pointer(k) + "/lerneintrag", v["lerneintrag"])
                   for k, v in (reg.get("fortsetzungen") or {}).items() if "lerneintrag" in v]
    for herkunft, v in kandidaten:
        if not isinstance(v, dict) or any(not isinstance(v.get(f), str) or not v[f].strip()
                                         for f in ("datum", "text", "quelle", "pruefstand")):
            raise ValueError(f"Unvollständige Beobachtung: {herkunft} (datum/text/quelle/pruefstand nötig)")
    return kandidaten


def importieren(conn, register):
    """Spiegelt das Register vollständig in die Datenbank. Gibt die Zählung je Tabelle zurück.

    Lerneintrag (gpt-6.1-sol, 2026-11-07): Falle: Quellenfreitext ist kein Knotenpfad.
    Nur explizite Pfade übernehmen; Prüffall: test_quellenverweise_ohne_graph_oder_erfundene_pfade.
    """
    rohtext = Path(register).read_bytes()
    reg = json.loads(rohtext.decode("utf-8"))
    if not isinstance(reg, dict):
        raise ValueError("Register ist kein JSON-Objekt")
    items = reg.get("items") or {}
    repos = reg.get("repos") or []
    fort = reg.get("fortsetzungen") or {}
    steuerung = reg.get("fortsetzungssteuerung") or {}
    ereignisse = reg.get("github_ereignisse") or {}
    beobachtungen = register_beobachtungen(reg)
    pfade = [r.get("pfad") for r in repos]
    if len(set(pfade)) != len(pfade) or None in pfade:
        raise ValueError("Repos ohne eindeutigen Pfad im Register")
    with conn:
        for tabelle in ("eingaenge", "repos", "fortsetzungen", "steuerung", "ereignisse"):
            conn.execute(f"DELETE FROM {tabelle}")
        conn.executemany(
            "INSERT INTO eingaenge VALUES (?,?,?,?,?,?,?,?)",
            [(k, _text(v.get("art")), _text(v.get("pfad")), _text(v.get("status")), _text(v.get("version")),
              _text(v.get("erstmals")), _text(v.get("gesehen")), _json(v)) for k, v in items.items()])
        conn.executemany(
            "INSERT INTO repos VALUES (?,?,?,?,?)",
            [(r["pfad"], _text(r.get("head")), _text(r.get("datum")), _text(r.get("pruefbedarf")), _json(r))
             for r in repos])
        conn.executemany(
            "INSERT INTO fortsetzungen VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [(k, projekt_von(k), *(_text(v.get(f)) for f in (
                "status", "typ", "wartet_auf", "frage", "antwort_genuegt", "danach", "seit", "wiederaufnahme")),
              _json(v), _text(v.get("knotenpfad"))) for k, v in fort.items()])
        conn.executemany("INSERT INTO steuerung VALUES (?,?)", [(k, _json(v)) for k, v in steuerung.items()])
        conn.executemany("INSERT INTO ereignisse VALUES (?,?)", [(k, _json(v)) for k, v in ereignisse.items()])
        # Nur Register-Spiegelzeilen ersetzen; Altbestände ohne Registerherkunft bleiben erhalten.
        behalten = {k for k, _ in beobachtungen}
        for (k,) in conn.execute("SELECT register_schluessel FROM beobachtungen "
                                 "WHERE register_schluessel IS NOT NULL").fetchall():
            if k not in behalten:
                conn.execute("DELETE FROM beobachtungen WHERE register_schluessel=?", (k,))
        conn.executemany(
            "INSERT INTO beobachtungen (register_schluessel,datum,text,quelle,pruefstand) VALUES (?,?,?,?,?) "
            "ON CONFLICT(register_schluessel) DO UPDATE SET datum=excluded.datum,text=excluded.text,"
            "quelle=excluded.quelle,pruefstand=excluded.pruefstand",
            [(k, v["datum"], v["text"], v["quelle"], v["pruefstand"]) for k, v in beobachtungen])
        conn.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", [
            ("register_sha256", hashlib.sha256(rohtext).hexdigest()),
            ("importiert", datetime.now().astimezone().isoformat(timespec="seconds"))])
    return zaehlung(conn)


TABELLEN = ("eingaenge", "repos", "fortsetzungen", "steuerung", "ereignisse", "beobachtungen")


def zaehlung(conn):
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABELLEN}


def json_zaehlung(register):
    reg = register_laden(register)
    return {"eingaenge": len(reg.get("items") or {}), "repos": len(reg.get("repos") or []),
            "fortsetzungen": len(reg.get("fortsetzungen") or {}),
            "steuerung": len(reg.get("fortsetzungssteuerung") or {}),
            "ereignisse": len(reg.get("github_ereignisse") or {}),
            "beobachtungen": len(register_beobachtungen(reg))}


# ---- „Wartet auf dich“ ---------------------------------------------------------------------------

def an_person(wartet_auf):
    """Leere Zuordnung, 'person' oder der Instanzname bezeichnet die besitzende Person."""
    from kern_adapter import lade_kern
    name = lade_kern(wurzel()).name().casefold()
    return not (wartet_auf or '').strip() or (wartet_auf or '').strip().casefold() in {'person', name}




def offene(conn):
    """(an_person, an_dritte): Fortsetzungen mit Frage, deren Status sie nicht als erledigt ausweist."""
    zeilen = conn.execute(
        "SELECT schluessel, projekt, status, wartet_auf, frage, antwort_genuegt, seit, knotenpfad, daten FROM fortsetzungen "
        "WHERE frage IS NOT NULL AND TRIM(frage) <> '' ORDER BY projekt, seit, schluessel").fetchall()
    offen = [z for z in zeilen if not ERLEDIGT.search(z[2] or "")]
    return [z for z in offen if an_person(z[3])], [z for z in offen if not an_person(z[3])]


def kurz(text, grenze=KURZ):
    text = " ".join((text or "").split())
    if len(text) <= grenze:
        return text
    return text[:grenze].rsplit(" ", 1)[0].rstrip(",;:.–- ") + " …"


def _gruppen(zeilen, mit_wer=False):
    zeilen_aus, projekt = [], None
    for _, proj, _, wer, frage, antwort, seit, knotenpfad, daten in zeilen:
        if proj != projekt:
            zeilen_aus.append(proj)
            projekt = proj
        wer_text = f"[{kurz(wer, 40)}] " if mit_wer else ""
        zeilen_aus.append(f"  - {wer_text}{kurz(frage)}")
        verweise = []
        if knotenpfad:
            verweise.append(f"Knoten: {knotenpfad}")
        quelle = _text(json.loads(daten).get("quelle"))
        if quelle:
            verweise.append(f"Quelle: {quelle}")
        zeilen_aus.append(f"    Antwort: {kurz(antwort) or 'offen'}" + (f" · seit {seit}" if seit else "")
                         + (" · " + " · ".join(verweise) if verweise else ""))
    return zeilen_aus


def wartet_text(conn):
    person, dritte = offene(conn)
    zeilen = [f"WARTET AUF DICH ({len(person)})" if person else "Nichts wartet auf dich."]
    zeilen += _gruppen(person)
    if dritte:
        zeilen += ["", f"WARTET AUF DRITTE, nicht auf dich ({len(dritte)})"] + _gruppen(dritte, mit_wer=True)
    return "\n".join(zeilen)


def veraltet(conn, register):
    """True, wenn das Register seit dem letzten Import geändert wurde."""
    if not Path(register).exists():
        return False
    aktuell = hashlib.sha256(Path(register).read_bytes()).hexdigest()
    gespeichert = conn.execute("SELECT wert FROM meta WHERE schluessel='register_sha256'").fetchone()
    return not gespeichert or gespeichert[0] != aktuell


def weiter_auswahl(reg):
    """Nur explizit übernommene Aufträge; keine Freigabe aus offenen Fragen ableiten.

    Direkt aus der zuständigen JSON, nicht aus einem eventuell alten DB-Spiegel.
    Ein fremder Blocker ist keine globale Sperre. Aktive Bearbeiter und Originalstand
    müssen vor dem Start weiterhin frisch in T3 geprüft werden.
    """
    steuerung = reg.get("fortsetzungssteuerung") or {}
    ergebnis = {"zustand": "leerlauf", "bereit": [], "klaeren": [], "pruefen": [],
                "hinweis": "Keine Startfreigabe: Original, T3-Bearbeiter und Budgets frisch prüfen. "
                           "Eine leere Auswahl belegt keine Ausschöpfung ungelesener Übergaben."}
    if steuerung.get("angehalten") is not False:
        ergebnis["zustand"] = "angehalten" if steuerung.get("angehalten") is True else "steuerung_fehlt"
        return ergebnis
    for kennung, auftrag in (reg.get("fortsetzungen") or {}).items():
        if auftrag.get("status") != "bereit_zur_uebernahme":
            continue
        pflicht = ("originalauftrag", "zielprojekt", "quelle", "checkpoint", "naechster_schritt")
        if (any(not isinstance(auftrag.get(f), str) or not auftrag[f].strip() for f in pflicht)
                or auftrag.get("pausiert") or auftrag.get("blocker") or auftrag.get("wartet_auf")):
            ergebnis["klaeren"].append(kennung)
            continue
        ergebnis["bereit"].append({"kennung": kennung, **{f: auftrag[f] for f in pflicht}})
    if ergebnis["bereit"]:
        ergebnis["zustand"] = "weiterarbeiten"
    # Scan und Lektüre sind verschieden. Ungelesene aktuelle Übergaben müssen als
    # konkrete Kandidaten sichtbar sein, auch wenn kein Auftrag schon bereit heißt.
    for kennung, quelle in (reg.get("items") or {}).items():
        repo_uebergabe = (quelle.get("art") == "repo-uebergabe"
                         and quelle.get("dateikategorie") == "Übergabe")
        todo = (steuerung.get("obsidian_im_loop") is True
                and quelle.get("art") == "obsidian"
                and quelle.get("pfad") == (steuerung.get("einmalige_todo") or {}).get("datei"))
        if not repo_uebergabe and not todo:
            continue
        if quelle.get("pausiert"):
            continue
        sha = quelle.get("source_sha256")
        if todo:
            # Die ausgewählte Liste frisch prüfen, ohne den Vault zu inventarisieren.
            try:
                sha = hashlib.sha256(Path(quelle["pfad"]).read_bytes()).hexdigest()
            except OSError:
                sha = None  # Zugangslücke bleibt ein Prüfkandidat.
        if not sha or quelle.get("gelesen_sha256") != sha:
            ergebnis["pruefen"].append({"kennung": kennung, "quelle": quelle.get("pfad"),
                                       "checkpoint": sha, "repo": quelle.get("repo")})
    # L30 (10.11.2026): "abgleich_noetig" nur mit offenen Kandidaten; ohne sie ist es Leerlauf.
    if ergebnis["zustand"] == "leerlauf" and (ergebnis["klaeren"] or ergebnis["pruefen"]):
        ergebnis["zustand"] = "abgleich_noetig"
    return ergebnis


def weiter_exit(ergebnis, abschluss=False):
    # Nur tatsächlichen Leerlauf prüfen. Warten auf eine asynchrone Rückgabe ist
    # nach dem T3-next-Vertrag kein Abschluss und benutzt diesen Schalter nicht.
    return 3 if (ergebnis["zustand"] == "steuerung_fehlt" or
                 (abschluss and (ergebnis["bereit"] or ergebnis["klaeren"]
                                 or ergebnis.get("pruefen")))) else 0


# ---- Befehle -------------------------------------------------------------------------------------

def main(argv):
    wurzel = Path(os.environ.get("KOMPASS_DIR") or INSTANZ).resolve()
    register, datenbank = wurzel / REGISTER, wurzel / DATENBANK
    befehl = argv[0] if argv else ""
    if befehl == "weiter":
        if argv[1:] not in ([], ["--abschluss"]):
            print("weiter [--abschluss]", file=sys.stderr)
            return 2
        try:
            ergebnis = weiter_auswahl(register_laden(register))
        except (OSError, ValueError, TypeError, AttributeError) as error:
            print(f"weiter: Register nicht auswertbar: {error}", file=sys.stderr)
            return 1
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        return weiter_exit(ergebnis, abschluss="--abschluss" in argv)
    if befehl == "import":
        if not register.exists():
            print(f"db-import: Register fehlt: {register}", file=sys.stderr)
            return 1
        conn = verbinden(datenbank)
        zaehl, soll = importieren(conn, register), json_zaehlung(register)
        # Frühere Beobachtungen ohne Registerkennung werden nicht als JSON-Abweichung gewertet.
        soll["beobachtungen"] += conn.execute(
            "SELECT COUNT(*) FROM beobachtungen WHERE register_schluessel IS NULL").fetchone()[0]
        for tabelle in TABELLEN:
            if tabelle in soll:
                print(f"{tabelle}: {zaehl[tabelle]}" + ("" if zaehl[tabelle] == soll[tabelle] else f" (JSON {soll[tabelle]}: ABWEICHUNG)"))
            else:
                print(f"{tabelle}: {zaehl[tabelle]} (kein Register-Schlüssel)")
        print(f"Datenbank: {datenbank} · Register unverändert maßgeblich")
        return 0 if all(zaehl[t] == soll[t] for t in soll) else 1
    if befehl == "wartet":
        if not datenbank.exists():
            print("wartet: keine Datenbank, zuerst `kompass db-import`", file=sys.stderr)
            return 1
        conn = verbinden(datenbank)
        print(wartet_text(conn))
        if veraltet(conn, register):
            print("\n(Register seit dem letzten db-import geändert: `kompass db-import`)")
        return 0
    print("dirigent_db.py import|wartet|weiter [--abschluss]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
