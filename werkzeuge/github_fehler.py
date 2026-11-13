#!/usr/bin/env python3
"""Einzelnen GitHub-Workflowfehler frisch lesen und im vorhandenen Eingang erfassen.

`--kontingente [--falls-alt]` summiert Actions-abrechenbaren Speicher je privatem Repo (auch archivierte) und die Kosten des Monats;
`--mails [Tage]` listet Kontomitteilungen von GitHub aus dem lokalen Mail-Index;
`--speicher-raeumen` löscht Artefakte archivierter Repos (nach expliziter Beauftragung).
`--uebersicht [--falls-alt]` liest zusätzlich alle eigenen Repos und speichert die roten Workflows
für die Startausgabe (nach expliziter Beauftragung).
Kein Webhookserver und kein Agentenstart. T3-Kontext stammt aus frischen
t3_project_list/t3_thread_list-Antworten; die Ausgabe nennt nur Kandidaten.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time

from eingang import atomic
from konfiguration import felder
from kern_adapter import lade_kern
import wissen


def positiv(value):
    if type(value) is not int or value < 1:
        raise ValueError('Positive Originalkennung fehlt')
    return value


def api(path):
    result = subprocess.run(['gh', 'api', '--method', 'GET', path],
                            capture_output=True, text=True, timeout=30, check=True)
    return json.loads(result.stdout)


def original(repo, lauf_id, auswahl, conclusions, repo_id_erwartet=None, versuch_erwartet=None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Ungültige Repo-Adresse')
    if repo.casefold() not in {x.casefold() for x in auswahl}:
        raise ValueError('Repo außerhalb der gewählten Quelle')
    positiv(lauf_id)
    repository = api(f'repos/{repo}')
    repo_id = positiv(repository['id'])
    if repo_id_erwartet is not None and repo_id != positiv(repo_id_erwartet):
        raise ValueError('Ereignis und Original nennen verschiedene Repo-IDs')
    name = repository['full_name']
    if name.casefold() != repo.casefold():
        raise ValueError('Repo umbenannt oder weitergeleitet; Auswahl erneut prüfen')
    run = api(f'repos/{name}/actions/runs/{lauf_id}')
    if (run['id'] != lauf_id or run['repository']['id'] != repo_id or
            run['repository']['full_name'].casefold() != name.casefold()):
        raise ValueError('Originalkennungen von Repo und Lauf widersprechen sich')
    if run['status'] != 'completed' or run['conclusion'] not in conclusions:
        raise ValueError('Kein abgeschlossener Fehlerlauf der gewählten Quelle')
    attempt = positiv(run['run_attempt'])
    if versuch_erwartet is not None and attempt != positiv(versuch_erwartet):
        raise ValueError('Ereignis nennt einen überholten Laufversuch')
    sha = run['head_sha']
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Original-Head fehlt')
    # PR-Zuordnung nur aus dem Original, nie aus Branch-/Auftragstiteln erraten.
    prs = sorted({positiv(pr['number']) for pr in run['pull_requests']
                  if pr['base']['repo']['id'] == repo_id})
    return {'kennung': f'github:{repo_id}:workflow_run:{lauf_id}:{attempt}',
            'repository_id': repo_id, 'repo': name, 'lauf_id': lauf_id,
            'run_attempt': attempt, 'head_sha': sha, 'conclusion': run['conclusion'],
            'original_aktualisiert': run['updated_at'], 'prs': prs,
            'url': f'https://github.com/{name}/actions/runs/{lauf_id}'}


def zuordnen(event, kontext):
    projekte = kontext.get('projekte', {})
    faeden = kontext.get('faeden', {})
    if ('nextCursor' not in projekte or projekte['nextCursor'] is not None or
            'nextCursor' not in faeden or faeden['nextCursor'] is not None):
        return {'status': 't3_abgleich_unvollstaendig'}
    key = f"github.com/{event['repo']}".casefold()
    projects = []
    for project in projekte['projects']:
        identity = project.get('repositoryIdentity') or {}
        # Ein Fork-Arbeitsbaum ist nicht der Bearbeiter seines Upstreams.
        origin = identity.get('origin') or identity
        if (not project.get('deletedAt') and not project.get('archivedAt') and
                str(origin.get('canonicalKey', '')).casefold() == key):
            projects.append(project)
    if len(projects) != 1:
        return {'status': 'projekt_offen', 'kandidaten': [x['id'] for x in projects]}
    project = projects[0]['id']
    threads = {}
    for thread in faeden['threads']:
        if thread.get('projectId') != project or thread.get('archived'):
            continue
        refs = [*thread.get('pullRequests', []), thread.get('linkedPullRequest')]
        if any(ref and str(ref.get('repository', '')).casefold() == event['repo'].casefold()
               and ref.get('number') in event['prs'] for ref in refs):
            threads[thread['threadId']] = thread
    if len(threads) != 1:
        return {'status': 'auftrag_offen', 'projectId': project, 'kandidaten': sorted(threads)}
    thread = next(iter(threads.values()))
    active = thread.get('status') in {'preparing', 'queued', 'starting', 'running', 'waiting'}
    return {'status': 'bearbeiter_aktiv' if active else 'originalauftrag_pruefen',
            'projectId': project, 'threadId': thread['threadId'],
            'link': thread.get('link'), 'settled': thread.get('settled', False)}


def erfassen(repo, lauf_id, kontext, root=None, state_path=None, repo_id_erwartet=None, versuch_erwartet=None):
    root = root or wissen.ROOT
    state_path = state_path or wissen.STATE
    raw = state_path.read_bytes()
    state = json.loads(raw)
    fm = lade_kern(root).frontmatter((root / 'kontextquellen.md').read_text())[0]
    event = original(repo, lauf_id, fm.get('github_workflow_repos', []),
                     fm.get('github_fehler_conclusions', []), repo_id_erwartet, versuch_erwartet)
    records = state.setdefault('github_ereignisse', {})
    previous = records.get(event['kennung'], {})
    route = zuordnen(event, kontext)
    paused = state.get('fortsetzungssteuerung', {}).get('angehalten') is not False
    record = {**previous, **event, 'erfasst': previous.get('erfasst', wissen.stamp()),
              'original_geprueft': wissen.stamp(), 'zuordnung': route}
    records[event['kennung']] = record
    if state_path.read_bytes() != raw:
        raise RuntimeError('Eingangsregister zwischenzeitlich geändert; nicht überschrieben')
    atomic(state_path, json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    return {**record, 'wiederholung': bool(previous), 'angehalten': paused,
            'zustellung': 'nicht_ausgefuehrt',
            'naechster_schritt': 'Pause erhalten' if paused else 'Originalauftrag und Blocker vor Zustellung prüfen'}


ROTLISTE = wissen.ROOT / '.zustand/github-rotliste.json'
KONTINGENTE = wissen.ROOT / '.zustand/github-kontingente.json'
ROTLISTE_MAX_STUNDEN = 12


def eigene_repos(api_fn=api, alle=False):
    """Eigene, nicht archivierte Repos ohne Forks; Forks melden fremde Workflows.

    `alle=True` liefert auch archivierte Repos und Forks mit Archiv-Kennzeichen: Speicher und Kosten
    zählt GitHub für jedes Repo des Kontos, auch für archivierte.
    """
    return sorted({r['full_name'] for r in repo_eintraege(api_fn)
                   if alle or (not r.get('fork') and not r.get('archived'))})


def repo_eintraege(api_fn=api):
    """Alle Repos des Kontos als API-Einträge (inklusive `private`, `archived`, `fork`)."""
    eintraege, seite = [], 1
    while True:
        teil = api_fn(f'user/repos?affiliation=owner&per_page=100&page={seite}')
        # GitHub liefert auch vor der letzten Seite manchmal weniger als 100; erst eine leere Seite beendet.
        if not teil or seite > 50:
            return eintraege
        eintraege += teil
        seite += 1


def rotliste(conclusions, api_fn=api, jetzt=None):
    """Je Workflow den letzten abgeschlossenen Lauf lesen; rot ist, was mit einem Fehler endete.

    Lesend, ohne Agentenstart. Grenze: nur die letzten 30 Läufe je Repo (ohne PR-Läufe);
    ein selten laufender Workflow kann dahinter verschwinden.
    """
    eintraege, fehler = [], []
    repos = eigene_repos(api_fn)
    for repo in repos:
        try:
            runs = api_fn(f'repos/{repo}/actions/runs?per_page=30&exclude_pull_requests=true')['workflow_runs']
        except (subprocess.SubprocessError, KeyError, ValueError):
            fehler.append(repo)
            continue
        letzte = {}
        for run in runs:
            if run.get('status') != 'completed':
                continue
            alt = letzte.get(run['workflow_id'])
            if alt is None or run['created_at'] > alt['created_at']:
                letzte[run['workflow_id']] = run
        for run in letzte.values():
            if run['conclusion'] in conclusions:
                eintraege.append({'repo': repo, 'workflow': run['name'], 'conclusion': run['conclusion'],
                                  'zeit': run['created_at'], 'ereignis': run.get('event'),
                                  'url': run['html_url']})
    eintraege.sort(key=lambda e: e['zeit'], reverse=True)
    return {'stand': jetzt or wissen.stamp(), 'repos_geprueft': len(repos) - len(fehler),
            'fehler': fehler, 'eintraege': eintraege}


def rotliste_erneuern(root=None, ziel=None, api_fn=api, nur_wenn_alt=False):
    root = root or wissen.ROOT
    ziel = ziel or ROTLISTE
    if nur_wenn_alt and ziel.exists():
        alter = time.time() - ziel.stat().st_mtime
        if alter < ROTLISTE_MAX_STUNDEN * 3600:
            return json.loads(ziel.read_text())
    fm = lade_kern(root).frontmatter((root / 'kontextquellen.md').read_text())[0]
    daten = rotliste(fm.get('github_fehler_conclusions', []), api_fn)
    atomic(ziel, json.dumps(daten, ensure_ascii=False, indent=2) + '\n')
    return daten


SPEICHER_GRENZE_BYTES = int(felder().get('github_speicher_grenze_bytes', 500 * 1024 * 1024))
SPEICHER_WARNUNG = 0.7


def artefakte(repo, api_fn=api):
    """Nicht abgelaufene Artefakte eines Repos als [(id, Bytes)], alle Seiten."""
    ergebnis, seite = [], 1
    while seite <= 20:
        teil = api_fn(f'repos/{repo}/actions/artifacts?per_page=100&page={seite}')['artifacts']
        if not teil:
            break
        ergebnis += [(a['id'], a['size_in_bytes']) for a in teil if not a.get('expired')]
        seite += 1
    return ergebnis


def kontingente(api_fn=api, jetzt=None):
    """Abrechenbarer Actions-Speicher je Repo und Kosten des Monats; lesend.

    Gezählt werden nur Artefakte privater Repos: öffentliche Repos sind kostenfrei, und der Cache
    (eigene 10-GB-Grenze je Repo) gehört nicht zum Speicherkontingent des Tarifs.

    Quelle der Kosten: Abrechnungs-API (Token-Scope `user`). Fehlt sie, bleibt `kosten_netto_eur` None,
    der Speicher wird trotzdem aus den Repos summiert.
    """
    jetzt = jetzt or datetime.now(timezone.utc)
    repos = sorted(r['full_name'] for r in repo_eintraege(api_fn) if r.get('private'))
    nicht_lesbar, je_repo = [], []
    for repo in repos:
        try:
            groesse = sum(b for _, b in artefakte(repo, api_fn))
        except (subprocess.SubprocessError, KeyError, ValueError):
            nicht_lesbar.append(repo)
            continue
        if groesse:
            je_repo.append({'repo': repo, 'bytes': groesse})
    je_repo.sort(key=lambda e: e['bytes'], reverse=True)
    kosten = None
    try:
        login = api_fn('user')['login']
        usage = api_fn(f'users/{login}/settings/billing/usage?year={jetzt.year}&month={jetzt.month}')
        kosten = round(sum(i.get('netAmount', 0) for i in usage['usageItems']), 2)
    except (subprocess.SubprocessError, KeyError, ValueError, TypeError):
        pass
    return {'stand': wissen.stamp(), 'grenze_bytes': SPEICHER_GRENZE_BYTES,
            'gesamt_bytes': sum(e['bytes'] for e in je_repo), 'je_repo': je_repo[:8],
            'kosten_netto_eur': kosten, 'nicht_lesbar': nicht_lesbar}


def speicher_raeumen(api_fn=api, loeschen_fn=None):
    """Artefakte ausschließlich in archivierten Repos löschen (reproduzierbare CI-Ausgaben ohne Weiterarbeit).

    Aktive Repos bleiben unberührt: dort können Artefakte zu einem Release gehören; Aufbewahrungsdauer
    (`retention-days`) wird über Issue/PR im Repo geändert, nicht von hier.
    """
    loeschen_fn = loeschen_fn or (lambda pfad: subprocess.run(
        ['gh', 'api', '--method', 'DELETE', pfad], capture_output=True, timeout=30, check=True))
    bericht = []
    for r in repo_eintraege(api_fn):
        if not r.get('archived'):
            continue
        geloescht = frei = 0
        for aid, groesse in artefakte(r['full_name'], api_fn):
            loeschen_fn(f"repos/{r['full_name']}/actions/artifacts/{aid}")
            geloescht += 1
            frei += groesse
        if geloescht:
            bericht.append({'repo': r['full_name'], 'artefakte': geloescht, 'bytes': frei})
    return bericht


ENVELOPE = Path.home() / 'Library/Mail/V10/MailData/Envelope Index'


def konto_mails(tage=3, db=None):
    """Kontomitteilungen von GitHub aus dem lokalen Apple-Mail-Index (alle Konten), nur lesend.

    Treffer: alle Mails von GitHub-Absendern außer `notifications@github.com` (Kontomitteilungen:
    Abrechnung, Sicherheit, Wochenübersicht).
    Repo-Benachrichtigungen (`notifications@github.com`) sind Rauschen; Workflowfehler eigener Repos
    kommen über die Rotliste.
    """
    import sqlite3
    db = db or ENVELOPE
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=5)
    try:
        zeilen = con.execute(
            "SELECT datetime(m.date_received,'unixepoch','localtime'), a.address, s.subject "
            "FROM messages m JOIN addresses a ON a.ROWID=m.sender JOIN subjects s ON s.ROWID=m.subject "
            "WHERE m.date_received > strftime('%s','now',?) AND (a.address='noreply@github.com' "
            "OR (a.address LIKE '%github.com' AND a.address != 'notifications@github.com')) "
            "ORDER BY m.date_received DESC", (f'-{int(tage)} days',)).fetchall()
    finally:
        con.close()
    return zeilen


def kontingente_erneuern(ziel=None, api_fn=api, nur_wenn_alt=False):
    """Ergebnis neben der Rotliste speichern; höchstens alle 12 h frisch lesen."""
    ziel = ziel or KONTINGENTE
    if nur_wenn_alt and ziel.exists() and time.time() - ziel.stat().st_mtime < ROTLISTE_MAX_STUNDEN * 3600:
        return json.loads(ziel.read_text())
    daten = kontingente(api_fn)
    atomic(ziel, json.dumps(daten, ensure_ascii=False, indent=2) + '\n')
    return daten


def kontingente_zeile(daten):
    anteil = daten['gesamt_bytes'] / daten['grenze_bytes']
    zeile = f"ACTIONS-SPEICHER: {daten['gesamt_bytes'] / 2**20:.0f} MB von {daten['grenze_bytes'] / 2**20:.0f} MB ({anteil:.0%})"
    if anteil >= SPEICHER_WARNUNG:
        zeile += f" · WARNUNG, größtes Repo: {daten['je_repo'][0]['repo']}"
    if daten.get('kosten_netto_eur'):
        zeile += f" · KOSTEN diesen Monat: {daten['kosten_netto_eur']} €"
    return zeile


def status_zeile(ziel=None, heute=None, frisch_tage=7):
    """Eine Zeile für die Startausgabe aus dem zuletzt gespeicherten Abgleich, ohne Netzaufruf."""
    ziel = ziel or ROTLISTE
    if not ziel.exists():
        return 'GITHUB-FEHLER: noch kein Abgleich; kompass github-fehler --uebersicht'
    daten = json.loads(ziel.read_text())
    heute = heute or datetime.now(timezone.utc)
    stand = datetime.fromisoformat(daten['stand'])
    veraltet = ' · VERALTET' if (heute - stand).days >= 2 else ''
    eintraege = daten['eintraege']
    if not eintraege:
        return f"GITHUB-FEHLER: keine roten Workflows in {daten['repos_geprueft']} Repos (Abgleich {daten['stand'][:16]}){veraltet}"
    grenze = heute - timedelta(days=frisch_tage)
    frisch = [e for e in eintraege
              if datetime.fromisoformat(e['zeit'].replace('Z', '+00:00')) >= grenze]
    repos = len({e['repo'] for e in eintraege})
    zeile = (f"GITHUB-FEHLER: {len(eintraege)} Workflows rot in {repos} Repos "
             f"(Abgleich {daten['stand'][:16]}{veraltet})")
    if frisch:
        namen = ', '.join(f"{e['repo'].split('/')[-1]}/{e['workflow']}" for e in frisch[:4])
        zeile += f"\n  neu seit {frisch_tage} T: {namen}" + (' …' if len(frisch) > 4 else '')
    if daten.get('fehler'):
        zeile += f"\n  nicht lesbar: {', '.join(daten['fehler'])}"
    return zeile + '\n  Liste: kompass github-fehler --uebersicht'


def kontingent_status(ziel=None):
    """Eine Startzeile aus dem gespeicherten Stand, nur bei Warnung oder Kosten; sonst leer."""
    ziel = ziel or KONTINGENTE
    if not ziel.exists():
        return ''
    daten = json.loads(ziel.read_text())
    if daten['gesamt_bytes'] / daten['grenze_bytes'] >= SPEICHER_WARNUNG or daten.get('kosten_netto_eur'):
        return kontingente_zeile(daten)
    return ''


def uebersicht_ausgeben(daten):
    for e in daten['eintraege']:
        print(f"{e['zeit'][:10]}  {e['conclusion']:<15} {e['repo']} · {e['workflow']}\n            {e['url']}")
    print(f"{len(daten['eintraege'])} rot · {daten['repos_geprueft']} Repos gelesen · Stand {daten['stand'][:16]}")
    if daten['fehler']:
        print(f"nicht lesbar: {', '.join(daten['fehler'])}")


def main(argv):
    if argv[:1] == ['--uebersicht']:
        try:
            uebersicht_ausgeben(rotliste_erneuern(nur_wenn_alt='--falls-alt' in argv))
            return 0
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
            print('GitHub-Übersicht nicht erneuert: Anmeldung oder Netz prüfen.', file=sys.stderr)
            return 1
    if argv[:1] == ['--kontingente']:
        try:
            daten = kontingente_erneuern(nur_wenn_alt='--falls-alt' in argv)
            print(kontingente_zeile(daten))
            for e in daten['je_repo'][:3]:
                print(f"  {e['bytes'] / 2**20:7.0f} MB  {e['repo']}")
            return 0
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
            print('GitHub-Kontingente nicht gelesen: Anmeldung oder Netz prüfen.', file=sys.stderr)
            return 1
    if argv[:1] == ['--mails']:
        try:
            tage = int(argv[1]) if len(argv) > 1 else 3
            zeilen = konto_mails(tage)
            for zeit, absender, betreff in zeilen:
                print(f'{zeit[:16]}  {absender}  {betreff}')
            print(f'{len(zeilen)} Kontomitteilungen von GitHub in {tage} Tagen')
            return 0
        except (OSError, ValueError):
            print('Mail-Index nicht lesbar: Vollzugriff auf die Festplatte für das Terminal prüfen.', file=sys.stderr)
            return 1
    if argv[:1] == ['--speicher-raeumen']:
        try:
            bericht = speicher_raeumen()
            for b in bericht:
                print(f"gelöscht: {b['artefakte']} Artefakte, {b['bytes'] / 2**20:.0f} MB in {b['repo']}")
            print('nichts zu räumen (archivierte Repos ohne Artefakte)' if not bericht else '')
            kontingente_erneuern()
            return 0
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
            print('Speicher nicht geräumt: Anmeldung, Netz oder Rechte prüfen.', file=sys.stderr)
            return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo')
    parser.add_argument('lauf_id', type=int)
    parser.add_argument('--repo-id', type=int, help='Repo-ID aus dem Originalereignis zum Gegenabgleich')
    parser.add_argument('--versuch', type=int, help='run_attempt aus dem Originalereignis zum Gegenabgleich')
    parser.add_argument('--t3-kontext', type=Path,
                        help='JSON: projekte/faeden = vollständige frische T3-Listen samt nextCursor; sonst Zuordnung offen')
    args = parser.parse_args(argv)
    try:
        kontext = json.loads(args.t3_kontext.read_text()) if args.t3_kontext else {}
        print(json.dumps(erfassen(args.repo, args.lauf_id, kontext, repo_id_erwartet=args.repo_id,
                                  versuch_erwartet=args.versuch), ensure_ascii=False, indent=2))
        return 0
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, RuntimeError):
        # Keine rohen CLI-Fehler oder Payloads mit möglichen Zugangsinformationen ausgeben.
        print('GitHub-Fehler nicht erfasst: Auswahl, Originale, T3-Kontext oder Registerkonflikt prüfen.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
