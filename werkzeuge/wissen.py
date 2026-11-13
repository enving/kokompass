#!/usr/bin/env python3
"""Lokales Eingangsregister: entdecken != lesen != ins Wiki einarbeiten.

scan inventarisiert nur Metadaten externer Dateien. Keine API, Transkription oder Löschung.
status liest den letzten Lauf. Erledigt-Markierungen sind an eine Dateiversion gebunden.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote

from eingang import atomic, digest
from konfiguration import wurzel, felder, pfad, vault_pfad

ROOT = wurzel()
HOME = Path.home()
VAULT = vault_pfad(ROOT)
STATE = ROOT / ".zustand/eingaenge.json"
TEXT = {".md", ".mdx", ".txt", ".html", ".docx", ".pdf"}
MEDIA = {".mp4", ".mov", ".webm", ".m4a", ".mp3", ".wav", ".png", ".jpg", ".jpeg", ".webp"}


def stamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def repo_paths():
    """Lokale Repo-Wurzeln plus ausdrücklich im Kompass verknüpfte lokale Repos."""
    roots = set()
    for base in (pfad(p, ROOT) for p in felder(ROOT).get('repo_wurzeln', [])):
        if base.exists():
            for p in base.iterdir():
                if p.is_dir() and (p / '.git').exists() and p.resolve() != ROOT.resolve():
                    roots.add(p.resolve())
    from kern_adapter import lade_kern
    roots.update(pfad(p, ROOT) for p in felder(ROOT).get('repo_pfade', []))
    for node in lade_kern(ROOT).laden().values():
        value = node['fm'].get('repo')
        if isinstance(value, str):
            path = pfad(value, ROOT) if not value.startswith(('https://', 'http://', 'git@')) else None
            if path is not None and path.resolve() != ROOT.resolve():
                roots.add(path.resolve())
    return sorted(roots)


def handoff_files(repo):
    """Git-Dateiliste plus ignorierte Wurzelübergaben; keine Inhalte auswerten."""
    repo = repo.resolve()
    found = subprocess.run(['git', '-C', str(repo), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                           capture_output=True, timeout=15)
    if found.returncode:
        raise RuntimeError(f'Übergabe-Dateiliste nicht lesbar: {repo}')
    paths = {repo / os.fsdecode(name) for name in found.stdout.split(b'\0') if name}
    paths.update(repo.iterdir())
    return sorted(p for p in paths if p.name.casefold() in ('uebergabe.md', 'übergabe.md', 'handoff.md')
                  and p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(repo))


def handoff_kind(path, repo):
    parts = [s.casefold() for s in path.relative_to(repo).parts[:-1]]
    if any(s.startswith('archiv') for s in parts):
        return 'Archiv'
    if any(s in ('skills', 'workflows', 'references', 'templates', 'vorlagen') for s in parts):
        return 'Vorlage/Anleitung'
    return 'Übergabe'


def discover():
    for p in (VAULT.rglob("*") if VAULT else []):
        rel = p.relative_to(VAULT)
        if any(x.startswith(".") for x in rel.parts) or rel.parts[0] in ("wiki", "Wiki", "aktionen"):
            continue
        if rel.parts[:2] == ("Kompass", "Knoten") or rel.parts[0] == "Kompass" and len(rel.parts) == 2:
            continue
        if p.is_file() and not p.is_symlink() and p.suffix.lower() in TEXT | MEDIA and p.name not in ("index.md", "AGENTS.md", "START.md"):
            yield "obsidian", p
    config = felder(ROOT)
    for key, kind, suffixes in [('eingang_movies', 'movies', MEDIA),
                                 ('eingang_downloads', 'downloads', TEXT | MEDIA),
                                 ('eingang_zulieferer', 'zulieferer', TEXT)]:
        base = pfad(config[key], ROOT) if config.get(key) else None
        if base and base.exists():
            for p in base.iterdir():
                if p.is_file() and not p.is_symlink() and p.suffix.lower() in suffixes:
                    yield kind, p
    if config.get('studio_wurzel'):
        channels = pfad(config['studio_wurzel'], ROOT)
        for pattern, kind in [("*/folgen/*/deck/anmerkungen/AUFTRAG.md", "studio-anmerkung"),
                              ("*/folgen/*/aufnahmen/session-*/session.json", "studio-aufnahme"),
                              ("*/folgen/*/sprechtext.md", "kanal-sprechtext"),
                              ("*/folgen/*/aufnahmen/session-*/transkript.md", "studio-transkript")]:
            for p in channels.glob(pattern):
                yield kind, p
    for repo in repo_paths():
        for p in handoff_files(repo):
            yield 'repo-uebergabe', p


def scan():
    raw = STATE.read_bytes() if STATE.exists() else None
    old = json.loads(raw) if raw else {"items": {}, "fortsetzungssteuerung": {"angehalten": True}, "fortsetzungen": {}}
    items = {}
    for kind, path in discover():
        s = path.stat()
        version = f"{s.st_size}:{s.st_mtime_ns}"
        key = hashlib.sha256(str(path).encode()).hexdigest()[:20]
        prior = old["items"].get(key, {})
        same = prior.get("version") == version and prior.get("status") != "nicht_mehr_am_pfad"
        items[key] = {**(prior if same else {}), "art": kind, "pfad": str(path), "version": version, "bytes": s.st_size,
                      "status": prior.get("status", "entdeckt") if same else "geaendert" if prior else "entdeckt",
                      "erstmals": prior.get("erstmals", stamp()), "gesehen": stamp(),
                      "wiki": prior.get("wiki", []) if same else [],
                      "gelesen": prior.get("gelesen", False) if same else False}
    for key, entry in old["items"].items():
        if key not in items:
            items[key] = {**entry, "status": "nicht_mehr_am_pfad"}
    state = {**old, "scan": stamp(), "umfang": "Explizite Ordner; kein vollständiger Mac- oder Browserimport", "items": items,
             "repos": scan_repos()}
    if (STATE.read_bytes() if STATE.exists() else None) != raw:
        raise RuntimeError('Eingangsregister zwischenzeitlich geändert; nicht überschrieben')
    atomic(STATE, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    report(state)
    status(state)


def scan_repos():
    """Git-Zustand und vorhandene Belege; liest nicht den gesamten Repository-Inhalt."""
    import graph
    evidence = {}
    for node, k in graph.laden().items():
        path = k['fm'].get('repo')
        if isinstance(path, str) and path:
            evidence[str(Path(path).expanduser().resolve())] = (node, k['fm'].get('geprueft_commit', ''))
    result = []
    for p in repo_paths():
        entry = {'pfad': str(p), 'inhaltlich_gelesen': False}
        def git(*args):
            done = subprocess.run(['git', '-C', str(p), *args], capture_output=True, text=True, timeout=8)
            if done.returncode:
                raise RuntimeError('Git-Abfrage fehlgeschlagen: ' + args[0])
            return done.stdout.strip()
        try:
            entry['head'] = git('rev-parse', 'HEAD')
            entry['datum'] = git('log', '-1', '--format=%ad', '--date=short')
            changes = git('status', '--porcelain')
            entry['offene_dateien'] = len(changes.splitlines()) if changes else 0
            entry['uebergaben'] = [str(q) for q in handoff_files(p)]
            node, checked = evidence.get(str(p), ('', ''))
            entry.update(beleg=node, geprueft_commit=checked)
            entry['pruefbedarf'] = 'kein Beleg' if not node else 'kein geprüfter Commit' if not checked else (
                'Änderungen seit Prüfung' if not entry['head'].startswith(checked) or changes else 'Commit entspricht Beleg')
        except (subprocess.TimeoutExpired, RuntimeError, OSError) as exc:
            entry['fehler'] = str(exc)
        result.append(entry)
    return result


def handoffs():
    """Nur Repo-/Übergabestand erneuern; andere Eingänge und Pilotfelder erhalten."""
    raw = STATE.read_bytes() if STATE.exists() else None
    state = json.loads(raw) if raw else {'scan': stamp(), 'items': {}, 'repos': [], 'fortsetzungssteuerung': {'angehalten': True}, 'fortsetzungen': {}}
    state['repos'] = scan_repos()
    now, seen, errors = stamp(), set(), []
    failed = [Path(e['pfad']) for e in state['repos'] if e.get('fehler')]
    for repo in state['repos']:
        if repo.get('fehler'):
            errors.append(repo['fehler'])
        for name in repo.get('uebergaben', []):
            p = Path(name)
            key = digest(str(p).encode())[:20]
            seen.add(key)
            old = state['items'].get(key, {})
            try:
                a = p.stat()
                data = p.read_bytes()
                b = p.stat()
                if (a.st_size, a.st_mtime_ns) != (b.st_size, b.st_mtime_ns) or len(data) != a.st_size or data != p.read_bytes():
                    raise ValueError('nicht stabil lesbar')
                sha = digest(data)
                same = old.get('source_sha256') == sha and old.get('status') != 'nicht_mehr_am_pfad'
                entry = {**old, 'art': 'repo-uebergabe', 'pfad': name, 'repo': repo['pfad'],
                         'dateikategorie': handoff_kind(p, Path(repo['pfad'])),
                         'version': f'{a.st_size}:{a.st_mtime_ns}', 'bytes': len(data),
                         'source_sha256': sha, 'hash_geprueft': now, 'gesehen': now,
                         'erstmals': old.get('erstmals', now)}
                if not same:
                    entry.update(status='geaendert' if old else 'entdeckt', gelesen=False, wiki=[])
                entry.pop('lesefehler', None)
                state['items'][key] = entry
            except (OSError, ValueError) as exc:
                errors.append(f'{p}: {exc}')
                state['items'][key] = {**old, 'art': 'repo-uebergabe', 'pfad': name,
                                       'status': old.get('status', 'entdeckt'), 'lesefehler': str(exc)}
    for key, item in state['items'].items():
        if item['art'] == 'repo-uebergabe' and key not in seen:
            if any(Path(item['pfad']).is_relative_to(p) for p in failed):
                continue
            if not Path(item['pfad']).is_file():
                item['status'] = 'nicht_mehr_am_pfad'
    state['repo_scan'] = now
    if (STATE.read_bytes() if STATE.exists() else None) != raw:
        raise RuntimeError('Eingangsregister zwischenzeitlich geändert; nicht überschrieben')
    atomic(STATE, json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    report(state)
    print(f'Übergaben: {len(seen)} verlinkt, {len(errors)} Fehler. Nur Erfassung, keine Lektüre oder Beauftragung.')
    for error in errors:
        print('FEHLER:', error)
    return bool(errors)


def report(state):
    rows = ["---", "type: Bericht", "title: Eingänge und Erfassungslücken", "vertraulich: ja",
            f"timestamp: {state.get('repo_scan', state['scan'])}", "---", "", "# Eingänge und Erfassungslücken", "",
            "Erzeugtes Register. **Entdeckt bedeutet nur: Pfad und Dateimetadaten gesehen.**", "",
            f"Breiter Eingangsscan: {state['scan']}. Der getrennte Repo-/Übergabeabgleich steht unten.", "",
            "Keine Browser-Sitzung, kein NotebookLM-Inhalt und keine Immich-Bildsammlung wird hier ausgelesen.",
            "Downloads und Movies werden nur direkt, nicht rekursiv durchsucht. Repos siehe Bestandsprüfung.", "",
            "| Eingang | Vorhandene Dateien |", "|---|---:|"]
    active = {k: v for k, v in state["items"].items() if v["status"] != "nicht_mehr_am_pfad"}
    for kind, number in sorted(Counter(x["art"] for x in active.values()).items()):
        rows.append(f"| {kind} | {number} |")
    rows += ["", "## Einzeldateien", "", "| ID | Eingang | Datei | Status |", "|---|---|---|---|"]
    for key, e in sorted(active.items(), key=lambda kv: (kv[1]["art"], kv[1]["pfad"])):
        p = Path(e["pfad"])
        note = e['status'] + (f"; {e['dateikategorie']} (keine Freigabe)" if e.get('dateikategorie') else '')
        note += f"; LESEFEHLER: {e['lesefehler']}" if e.get('lesefehler') else ''
        rows.append(f"| `{key}` | {e['art']} | [{p.name.replace('|', '–')}]({p.as_uri()}) | {note.replace('|', '–')} |")
    rows += ['', '## Repositories', '',
             'Nur Git-Metadaten geprüft, keine vollständige Code-Lektüre. Erfasst sind konfigurierte Repo-Wurzeln und lokale repo-Verweise im Kompass; verschachtelte Submodule nicht vollständig.', '',
             f"Repo-/Übergabeabgleich: {state.get('repo_scan', state['scan'])}. Übergaben sind nur verlinkt, nicht fachlich geprüft oder beauftragt.",
             'Dateiumfang: Git-Dateiliste (versioniert und nicht ignoriert), zusätzlich ignorierte Übergaben direkt in der Repo-Wurzel. Keine vollständige Erfassung ignorierter Unterordner oder externer Arbeitsbäume.',
             'Archivpfade und Vorlagen/Anleitungen sind als solche gekennzeichnet. Auch „Übergabe“ ist nur eine Dateikategorie, kein offener oder freigegebener Auftrag.', '',
             '| Repository | Letzter Commit | Offene Dateien | Prüfung | Übergaben |', '|---|---|---:|---|---|']
    for entry in state.get('repos', []):
        p = Path(entry['pfad'])
        links = ', '.join(f"[{Path(q).relative_to(p).as_posix().replace('|', '–')} ({handoff_kind(Path(q), p)})]({Path(q).as_uri()})" for q in entry.get('uebergaben', [])) or '—'
        rows.append(f"| [{p.name}]({p.as_uri()}) | {entry.get('datum', '?')} | {entry.get('offene_dateien', '?')} | {entry.get('fehler', entry.get('pruefbedarf', '?'))} | {links} |")
    rows += ["", "## Wie daraus Wissen wird", "",
             "`kompass eingang` sichert Textquellen aus Obsidian vollständig. Ein Agent liest anschließend die Quelle, "
             "pflegt die betroffenen Seiten und protokolliert Quellhash, Modell und Datum. "
             "Videos benötigen zunächst eine beauftragte Transkription; Bilder eine Sichtprüfung. "
             "Browser-Ergebnisse müssen als Datei/Export oder mit zugänglichem Link abgelegt werden.", "",
             "Erst danach: `python3 werkzeuge/wissen.py erledigt <ID> <Wiki-Datei> [weitere Wiki-Dateien]`.", ""]
    atomic(ROOT / "berichte/eingaenge.md", "\n".join(rows))


def status(state=None):
    if state is None:
        if not STATE.exists():
            print("WISSENSEINGANG: noch kein Scan; kompass scan")
            return
        state = json.loads(STATE.read_text())
    pending = [x for x in state["items"].values() if x["status"] in ("entdeckt", "geaendert", "teilweise_eingearbeitet")]
    print(f"WISSENSEINGANG: {len(pending)} Dateien ohne bestätigte Einarbeitung (Scan {state['scan'][:16]}).")
    print("  Register: berichte/eingaenge.md · aktualisieren: kompass scan · kein automatisches LLM.")
    tasks = state.get('aufgaben_abgleich')
    if tasks:
        gh = tasks['github']
        note = 'VERALTET/UNVOLLSTÄNDIG' if gh.get('fehler') else 'Originalstatus, keine Arbeitsfreigabe'
        print(f"KONTEXT: kompass kontext <Thema> erneuert Originalquellen beim Aufruf · letzter GitHub-Abgleich {gh.get('stand', 'noch ohne Erfolg')} · {note}")


def done(key, pages):
    state = json.loads(STATE.read_text())
    item = state["items"][key]
    p = Path(item["pfad"])
    s = p.stat()
    if item["version"] != f"{s.st_size}:{s.st_mtime_ns}":
        raise ValueError("Quelle seit Scan geändert; erst erneut scannen und lesen")
    destinations = []
    for page in pages:
        q = Path(page).expanduser().resolve()
        if not q.is_file() or not (q.is_relative_to(ROOT.resolve()) or (VAULT is not None and q.is_relative_to((VAULT / "wiki").resolve()))):
            raise ValueError(f"Keine bestehende Wiki-Datei: {page}")
        destinations.append(str(q))
    item.update(status="eingearbeitet", gelesen=True, wiki=destinations, verarbeitet=stamp())
    atomic(STATE, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    report(state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan")
    sub.add_parser("status")
    sub.add_parser("uebergaben")
    mark = sub.add_parser("erledigt")
    mark.add_argument("id")
    mark.add_argument("pages", nargs="+")
    args = parser.parse_args()
    if args.command == "scan":
        scan()
    elif args.command == "status":
        status()
    elif args.command == "uebergaben":
        raise SystemExit(1 if handoffs() else 0)
    else:
        done(args.id, args.pages)
