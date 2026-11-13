import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
"""Tests der Dirigenten-Datenbank. Alle Daten sind erfunden, nicht das echte Register."""
import json
import os
from unittest.mock import patch
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
import dirigent_db as db


def beispiel():
    return {
        "items": {"a1": {"art": "obsidian", "pfad": "/x/a.md", "status": "neu", "version": "1:2"},
                  "b2": {"art": "repo", "pfad": "/x/b.md", "bytes": 5}},
        "repos": [{"pfad": "/r/eins", "head": "abc", "datum": "2026-01-01", "pruefbedarf": "kein Beleg"},
                  {"pfad": "/r/zwei", "head": "def", "datum": "2026-01-02", "pruefbedarf": ""}],
        "fortsetzungen": {
            "alpha:12:abc": {"typ": "freigabe", "frage": "Alpha #12 integrieren?", "antwort_genuegt": "Ja oder Nein",
                             "seit": "2026-01-03", "wartet_auf": "person", "status": "geprueft_mit_befund"},
            "alpha:7:abc": {"typ": "freigabe", "frage": "Alpha #7 fertig", "status": "geprueft_abgenommen_erledigt"},
            "wartet:beta-login": {"typ": "zugang", "frage": "Beta-Anmeldung durchführen", "antwort_genuegt": "Login",
                                  "seit": "2026-01-04", "wartet_auf": None},
            "wartet:gamma-wipe": {"typ": "extern", "frage": "Bestätigung Gamma", "wartet_auf": "Erika (extern)",
                                  "antwort_genuegt": "Ja/Nein"},
            "wartet:delta-takt": {"typ": "entscheidung", "frage": "Takt?", "status": "dirigent_entschieden"},
            "alpha:lektuere": {"status": "vollstaendig_gelesen", "sha256": "00"},
        },
        "fortsetzungssteuerung": {"angehalten": False, "modus": "regulaer", "tiefer": {"a": [1, 2]}},
        "github_ereignisse": {"github:1": {"art": "lauf"}},
    }


class DbTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"KOMPASS_DIR": str(self.dir)})
        self.env.start()
        self.addCleanup(self.env.stop)
        (self.dir / "person").mkdir()
        (self.dir / "person/ich.md").write_text("---\ntype: Person\nname: Mara\n---\n")
        self.register = self.dir / "eingaenge.json"
        self.register.write_text(json.dumps(beispiel()), encoding="utf-8")
        self.conn = db.verbinden(self.dir / "dirigent.sqlite")

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_beobachtungen_import_wiederimport_und_quellstand(self):
        reg = beispiel()
        eintrag = {"datum": "2026-01-05", "text": "Quelltext nicht als Pfad deuten",
                   "quelle": "UEBERGABE.md#fallen", "pruefstand": "Commit abc; Test bestanden"}
        reg["beobachtungen"] = {"quelle/1": eintrag}
        reg["fortsetzungen"]["alpha:12:abc"]["lerneintrag"] = dict(eintrag, text="Zweite Beobachtung")
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        vorher = self.register.read_bytes()
        self.assertEqual(db.importieren(self.conn, self.register)["beobachtungen"], 2)
        zeilen = list(self.conn.execute("SELECT * FROM beobachtungen ORDER BY id"))
        db.importieren(self.conn, self.register)
        self.assertEqual(list(self.conn.execute("SELECT * FROM beobachtungen ORDER BY id")), zeilen)
        self.assertEqual(self.register.read_bytes(), vorher)
        row = self.conn.execute("SELECT quelle,pruefstand,register_schluessel FROM beobachtungen "
                                "WHERE text=?", (eintrag["text"],)).fetchone()
        self.assertEqual(row, (eintrag["quelle"], eintrag["pruefstand"], "/beobachtungen/quelle~11"))
        reg["beobachtungen"]["quelle/1"]["pruefstand"] = "Nachprüfung def"
        del reg["fortsetzungen"]["alpha:12:abc"]["lerneintrag"]
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        self.assertEqual(db.importieren(self.conn, self.register)["beobachtungen"], 1)
        self.assertEqual(self.conn.execute("SELECT id,pruefstand FROM beobachtungen").fetchone(),
                         (zeilen[0][0], "Nachprüfung def"))

    def test_unbelegte_beobachtung_bricht_ab_ohne_spiegel_zu_aendern(self):
        db.importieren(self.conn, self.register)
        reg = beispiel()
        reg["beobachtungen"] = {"unbelegt": {"datum": "2026-01-01", "text": "Behauptung"}}
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        vorher = [list(self.conn.execute(f"SELECT * FROM {t}")) for t in db.TABELLEN]
        with self.assertRaisesRegex(ValueError, "/beobachtungen/unbelegt"):
            db.importieren(self.conn, self.register)
        self.assertEqual([list(self.conn.execute(f"SELECT * FROM {t}")) for t in db.TABELLEN], vorher)

    def test_migration_erhaelt_alte_beobachtungen(self):
        alt = sqlite3.connect(":memory:")
        alt.executescript(db.MIGRATIONEN[0])
        alt.execute("PRAGMA user_version=1")
        alt.execute("INSERT INTO beobachtungen(datum,text,quelle,pruefstand) VALUES ('d','alt','q','p')")
        alt.commit()
        db.migrieren(alt)
        db.importieren(alt, self.register)
        self.assertEqual(alt.execute("SELECT text,register_schluessel FROM beobachtungen").fetchall(),
                         [("alt", None)])
        alt.close()

    def test_quellenverweise_ohne_graph_oder_erfundene_pfade(self):
        reg = beispiel()
        fall = reg["fortsetzungen"]["alpha:12:abc"]
        fall["knotenpfad"] = "belege/erfunden.md#an-person"
        fall["quelle"] = "UEBERGABE.md, Abschnitt 7; kein Knoten"
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        db.importieren(self.conn, self.register)
        self.assertIn("Knoten: " + fall["knotenpfad"], db.wartet_text(self.conn))
        self.assertIn("Quelle: " + fall["quelle"], db.wartet_text(self.conn))
        del fall["knotenpfad"]
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        db.importieren(self.conn, self.register)
        text = db.wartet_text(self.conn)
        self.assertNotIn("Knoten:", text)
        self.assertIn("Quelle: " + fall["quelle"], text)

    def test_schema_und_migrationsversion(self):
        self.assertEqual(db.version(self.conn), len(db.MIGRATIONEN))
        tabellen = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"eingaenge", "repos", "fortsetzungen", "steuerung", "ereignisse", "beobachtungen",
                         "meta"} <= tabellen)
        self.conn.close()
        self.conn = db.verbinden(self.dir / "dirigent.sqlite")  # erneutes Öffnen migriert nichts doppelt
        self.assertEqual(db.version(self.conn), len(db.MIGRATIONEN))

    def test_zu_neue_datenbank_wird_abgelehnt(self):
        self.conn.execute(f"PRAGMA user_version = {len(db.MIGRATIONEN) + 1}")
        self.conn.commit()
        with self.assertRaises(RuntimeError):
            db.migrieren(self.conn)

    def test_import_zaehlung_gleich_json_und_idempotent(self):
        erst = db.importieren(self.conn, self.register)
        self.assertEqual({k: erst[k] for k in db.json_zaehlung(self.register)}, db.json_zaehlung(self.register))
        self.assertEqual(erst, {"eingaenge": 2, "repos": 2, "fortsetzungen": 6, "steuerung": 3,
                                "ereignisse": 1, "beobachtungen": 0})
        stand = [list(self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")) for t in db.TABELLEN]
        self.assertEqual(db.importieren(self.conn, self.register), erst)
        self.assertEqual([list(self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")) for t in db.TABELLEN], stand)

    def test_import_spiegelt_aenderungen_und_loescht_nichts_im_register(self):
        vorher = self.register.read_bytes()
        db.importieren(self.conn, self.register)
        reg = beispiel()
        del reg["fortsetzungen"]["wartet:gamma-wipe"]
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        nachher = self.register.read_bytes()
        self.assertEqual(db.importieren(self.conn, self.register)["fortsetzungen"], 5)
        self.assertEqual(self.register.read_bytes(), nachher)
        self.assertNotEqual(vorher, nachher)  # Prüfung selbst kann fehlschlagen: Datei wurde wirklich geändert

    def test_register_bleibt_unveraendert(self):
        vorher = self.register.read_bytes()
        db.importieren(self.conn, self.register)
        self.assertEqual(self.register.read_bytes(), vorher)

    def test_felder_und_volle_daten(self):
        db.importieren(self.conn, self.register)
        zeile = self.conn.execute("SELECT typ, wartet_auf, frage, antwort_genuegt, seit, status, daten "
                                  "FROM fortsetzungen WHERE schluessel='alpha:12:abc'").fetchone()
        self.assertEqual(zeile[:6], ("freigabe", "person", "Alpha #12 integrieren?", "Ja oder Nein",
                                     "2026-01-03", "geprueft_mit_befund"))
        self.assertEqual(json.loads(zeile[6])["typ"], "freigabe")
        tief = self.conn.execute("SELECT daten FROM steuerung WHERE schluessel='tiefer'").fetchone()[0]
        self.assertEqual(json.loads(tief), {"a": [1, 2]})

    def test_nicht_text_wert_geht_nicht_verloren(self):
        reg = beispiel()
        reg["fortsetzungen"]["alpha:12:abc"]["seit"] = {"tag": "2026-01-03"}
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        db.importieren(self.conn, self.register)
        seit = self.conn.execute("SELECT seit FROM fortsetzungen WHERE schluessel='alpha:12:abc'").fetchone()[0]
        self.assertEqual(json.loads(seit), {"tag": "2026-01-03"})

    def test_doppelter_repo_pfad_bricht_ab_ohne_zu_aendern(self):
        db.importieren(self.conn, self.register)
        reg = beispiel()
        reg["repos"].append(dict(reg["repos"][0]))
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        with self.assertRaises(ValueError):
            db.importieren(self.conn, self.register)
        self.assertEqual(db.zaehlung(self.conn)["repos"], 2)

    def test_fehlende_schluessel_ergeben_leere_tabellen(self):
        self.register.write_text("{}", encoding="utf-8")
        z = db.importieren(self.conn, self.register)
        self.assertEqual(set(z.values()), {0})

    def test_projekt_zuordnung(self):
        faelle = {'alpha:1:abc': 'alpha', 'wartet:beta-dienst-offen': 'beta',
                  'wartet:extern-login': 'extern', 'neurepo:1:abc': 'neurepo'}
        with patch.object(db, 'PROJEKT_VON_PRAEFIX', {'beta-dienst': 'beta'}):
            for schluessel, soll in faelle.items():
                self.assertEqual(db.projekt_von(schluessel), soll)

    def test_wartet_gruppiert_trennt_dritte_und_blendet_erledigtes_aus(self):
        db.importieren(self.conn, self.register)
        text = db.wartet_text(self.conn)
        zeilen = text.splitlines()
        self.assertEqual(zeilen[0], "WARTET AUF DICH (2)")
        self.assertIn("alpha", zeilen)
        self.assertIn("beta", zeilen)
        self.assertLess(zeilen.index("alpha"), zeilen.index("beta"))
        self.assertIn("  - Alpha #12 integrieren?", zeilen)
        self.assertIn("    Antwort: Ja oder Nein · seit 2026-01-03", zeilen)
        self.assertIn("    Antwort: Login · seit 2026-01-04", zeilen)
        dritte = text.index("WARTET AUF DRITTE")
        self.assertGreater(text.index("Gamma"), dritte)
        self.assertLess(text.index("Beta-Anmeldung"), dritte)
        self.assertNotIn("Alpha #7", text)   # abgenommen
        self.assertNotIn("Takt?", text)      # vom Dirigenten entschieden
        self.assertNotIn("lektuere", text)   # ohne Frage

    def test_je_punkt_hoechstens_zwei_zeilen_und_gekuerzt(self):
        reg = beispiel()
        reg["fortsetzungen"]["alpha:12:abc"]["frage"] = "Lang " * 100 + "\nmit Umbruch"
        reg["fortsetzungen"]["alpha:12:abc"]["antwort_genuegt"] = "Antwort " * 100
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        db.importieren(self.conn, self.register)
        zeilen = db.wartet_text(self.conn).splitlines()
        i = next(n for n, z in enumerate(zeilen) if z.startswith("  - Lang"))
        self.assertTrue(zeilen[i].endswith("…"))
        self.assertLessEqual(len(zeilen[i]), db.KURZ + 12)
        self.assertTrue(zeilen[i + 1].startswith("    Antwort: "))
        self.assertNotIn("mit Umbruch", zeilen[i])

    def test_leerfall_nichts_wartet_auf_dich(self):
        reg = beispiel()
        reg["fortsetzungen"] = {"alpha:7:abc": {"frage": "alt", "status": "dirigent_erledigt"}}
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        db.importieren(self.conn, self.register)
        self.assertEqual(db.wartet_text(self.conn), "Nichts wartet auf dich.")

    def test_leerfall_mit_nur_dritten(self):
        reg = beispiel()
        reg["fortsetzungen"] = {"wartet:gamma-wipe": reg["fortsetzungen"]["wartet:gamma-wipe"]}
        self.register.write_text(json.dumps(reg), encoding="utf-8")
        db.importieren(self.conn, self.register)
        text = db.wartet_text(self.conn)
        self.assertTrue(text.startswith("Nichts wartet auf dich."))
        self.assertIn("WARTET AUF DRITTE, nicht auf dich (1)", text)
        self.assertIn("[Erika (extern)]", text)

    def test_person_erkennung(self):
        self.assertTrue(db.an_person(None))
        self.assertTrue(db.an_person(""))
        self.assertTrue(db.an_person("Mara"))
        self.assertFalse(db.an_person("kontakt (extern)"))

    def test_veraltet_erkennt_geaendertes_register(self):
        db.importieren(self.conn, self.register)
        self.assertFalse(db.veraltet(self.conn, self.register))
        self.register.write_text(json.dumps({**beispiel(), "repos": []}), encoding="utf-8")
        self.assertTrue(db.veraltet(self.conn, self.register))

    def test_befehle_ueber_kompass_dir(self):
        """Ende-zu-Ende über main() mit erfundenem Verzeichnis, nicht dem echten."""
        import contextlib
        import io
        import os
        (self.dir / ".zustand").mkdir()
        (self.dir / ".zustand/eingaenge.json").write_text(json.dumps(beispiel()), encoding="utf-8")
        alt = os.environ.get("KOMPASS_DIR")
        os.environ["KOMPASS_DIR"] = str(self.dir)
        try:
            ausgabe = io.StringIO()
            with contextlib.redirect_stdout(ausgabe), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(db.main(["wartet"]), 1)           # noch keine Datenbank
                self.assertEqual(db.main(["import"]), 0)
                self.assertEqual(db.main(["wartet"]), 0)
                self.assertEqual(db.main(["unbekannt"]), 2)
        finally:
            if alt is None:
                os.environ.pop("KOMPASS_DIR")
            else:
                os.environ["KOMPASS_DIR"] = alt
        self.assertIn("fortsetzungen: 6", ausgabe.getvalue())
        self.assertIn("WARTET AUF DICH (2)", ausgabe.getvalue())
        self.assertTrue(sqlite3.connect(self.dir / ".zustand/dirigent.sqlite").execute(
            "SELECT COUNT(*) FROM fortsetzungen").fetchone()[0] == 6)


class WeiterTest(unittest.TestCase):
    def test_nur_ausgewaehlte_todoliste_frisch_pruefen(self):
        with tempfile.TemporaryDirectory() as td:
            todo = Path(td) / "todo.md"
            todo.write_text("neu")
            reg = {"fortsetzungssteuerung": {"angehalten": False, "obsidian_im_loop": True,
                       "einmalige_todo": {"datei": str(todo)}}, "items": {
                       "todo": {"art": "obsidian", "pfad": str(todo), "gelesen_sha256": "alt"},
                       "privat": {"art": "obsidian", "pfad": "/nicht/lesen"}}}
            self.assertEqual([q["kennung"] for q in db.weiter_auswahl(reg)["pruefen"]], ["todo"])
            todo.unlink()
            self.assertEqual(db.weiter_exit(db.weiter_auswahl(reg), True), 3)

    def test_ungelesene_uebergabe_verhindert_leerlauf_trotz_fremdem_blocker(self):
        reg = {"fortsetzungssteuerung": {"angehalten": False},
               "fortsetzungen": {"pi": {"status": "blockiert"}}, "items": {
                   "neu": {"art": "repo-uebergabe", "dateikategorie": "Übergabe",
                           "pfad": "/repo/UEBERGABE.md", "source_sha256": "neu",
                           "gelesen_sha256": "alt"},
                   "vorlage": {"art": "repo-uebergabe", "dateikategorie": "Vorlage/Anleitung"}}}
        auswahl = db.weiter_auswahl(reg)
        self.assertEqual([q["kennung"] for q in auswahl["pruefen"]], ["neu"])
        self.assertFalse(auswahl["bereit"])
        self.assertEqual(db.weiter_exit(auswahl, True), 3)
        reg["items"]["neu"]["gelesen_sha256"] = "neu"
        self.assertEqual(db.weiter_exit(db.weiter_auswahl(reg), True), 0)

    def test_pi_blockiert_nicht_andere_bereite_arbeit(self):
        reg = {"fortsetzungssteuerung": {"angehalten": False}, "fortsetzungen": {
            "pi:1": {"status": "blockiert", "wartet_auf": "person"},
            "alpha:2": {"status": "bereit_zur_uebernahme", "originalauftrag": "Auftrag2",
                        "zielprojekt": "projekt-alpha", "quelle": "/r/UEBERGABE.md",
                        "checkpoint": "abc", "naechster_schritt": "Adapter testen"}}}
        ergebnis = db.weiter_auswahl(reg)
        self.assertEqual([e["kennung"] for e in ergebnis["bereit"]], ["alpha:2"])
        self.assertEqual(db.weiter_exit(ergebnis, abschluss=True), 3)
        self.assertEqual(db.weiter_exit(ergebnis, abschluss=False), 0)

    def test_stopp_gilt_global_auch_bei_bereiter_arbeit(self):
        reg = {"fortsetzungssteuerung": {"angehalten": True}, "fortsetzungen": {
            "alpha": {"status": "bereit_zur_uebernahme"}}}
        self.assertEqual(db.weiter_auswahl(reg)["zustand"], "angehalten")
        self.assertFalse(db.weiter_auswahl(reg)["bereit"])

    def test_ohne_freigabestand_kein_erfundener_auftrag(self):
        reg = {"fortsetzungssteuerung": {"angehalten": False}, "fortsetzungen": {
            "idee": {"status": "offen"}, "alt": {"status": "erledigt"},
            "unvollstaendig": {"status": "bereit_zur_uebernahme"}}}
        ergebnis = db.weiter_auswahl(reg)
        self.assertFalse(ergebnis["bereit"])
        self.assertIn("unvollstaendig", ergebnis["klaeren"])
        self.assertEqual(db.weiter_exit(ergebnis, abschluss=True), 3)

    def test_fehlende_steuerung_startet_nichts(self):
        self.assertEqual(db.weiter_auswahl({})["zustand"], "steuerung_fehlt")
        self.assertEqual(db.weiter_exit(db.weiter_auswahl({}), True), 3)

    def test_leerlauf_ohne_kandidaten_ist_kein_abgleich(self):
        # Prüffall L30 (10.11.2026): Ohne Kandidaten darf der Zustand nicht "abgleich_noetig" heißen.
        reg = {"fortsetzungssteuerung": {"angehalten": False},
               "fortsetzungen": {"idee": {"status": "offen"}}, "items": {}}
        ergebnis = db.weiter_auswahl(reg)
        self.assertEqual(ergebnis["zustand"], "leerlauf")
        self.assertEqual(db.weiter_exit(ergebnis, abschluss=True), 0)
        reg["items"] = {"neu": {"art": "repo-uebergabe", "dateikategorie": "Übergabe",
                                "pfad": "/repo/UEBERGABE.md", "source_sha256": "neu",
                                "gelesen_sha256": "alt"}}
        self.assertEqual(db.weiter_auswahl(reg)["zustand"], "abgleich_noetig")

    def test_cli_nutzt_frisches_register_ohne_db_und_schreibt_nichts(self):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".zustand").mkdir()
            register = root / db.REGISTER
            register.write_text(json.dumps({"fortsetzungssteuerung": {"angehalten": False},
                "fortsetzungen": {"alpha": {"status": "bereit_zur_uebernahme",
                "originalauftrag": "Auftrag", "zielprojekt": "p", "quelle": "/r/UEBERGABE.md",
                "checkpoint": "abc", "naechster_schritt": "testen"}}}))
            vorher = register.read_bytes()
            run = subprocess.run([sys.executable, str(Path(db.__file__)), "weiter", "--abschluss"],
                env={**os.environ, "KOMPASS_DIR": td}, capture_output=True, text=True)
            self.assertEqual(run.returncode, 3, run.stderr)
            self.assertEqual(json.loads(run.stdout)["bereit"][0]["kennung"], "alpha")
            self.assertEqual(register.read_bytes(), vorher)
            self.assertFalse((root / db.DATENBANK).exists())


if __name__ == "__main__":
    unittest.main()
