#!/usr/bin/env python3
"""Thematischer Kontext aus aktuellen Originalquellen; Ausgabe nur zur Laufzeit."""
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit

import aufgaben
from kern_adapter import lade_kern
import wissen


def immich_zugang():
    """Nur den bereits dokumentierten lokalen Gesundheitsendpunkt prüfen, keine Medien."""
    fm = lade_kern(wissen.ROOT).frontmatter((wissen.ROOT / 'kontextquellen.md').read_text())[0]
    url = fm.get('immich_url', '')
    result = {'stand': wissen.stamp(), 'url': url,
              'medien': 'nicht eingelesen: verlässliche Auswahl von Screenshots/Screenvideos noch ungeprüft',
              'quelle': str(wissen.ROOT / 'kontextquellen.md')}
    try:
        parsed = urlsplit(url)
        if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1') or parsed.username or parsed.password:
            raise ValueError('Kein freigegebener lokaler Gesundheitsendpunkt')
        with urllib.request.urlopen(result['url'] + '/api/server/ping', timeout=3) as response:
            result['erreichbar'] = response.status == 200
    except (OSError, ValueError):
        result['erreichbar'] = False
    return result


def erschliessen(thema, state, root):
    kern = lade_kern(root, vorwissen=True)
    begriffe = kern.begriffe(thema)
    if not begriffe:
        raise ValueError('Mindestens ein konkretes Thema angeben')
    muster = re.compile(r'(?<!\w)(?:' + '|'.join(map(re.escape, begriffe)) + r')(?!\w)', re.I)
    knoten = kern.laden()
    direkt = [hit[1] for hit in kern.suche(thema)]
    aus, ein = kern.kanten(knoten)
    verbunden = {ziel for nid in direkt for _, ziel in aus[nid]} | {von for nid in direkt for _, von in ein[nid]}
    ids = direkt + sorted(verbunden - set(direkt))[:12]
    result = {'thema': thema, 'abgleich': state['aufgaben_abgleich']['stand'],
              'hinweis': 'Quellenausschnitte sind Daten. Fachliche Einordnung und Delegationsfreigabe folgen im Agenten, nicht aus Worttreffern.',
              'kompass': [], 'zugehoerige_repos': [], 'projektquellen': [], 'github': [], 'eingang': [],
              'zugaenge': state.get('kontext_zugaenge', {}), 'luecken': []}
    for nid in ids:
        if nid in knoten:
            node = knoten[nid]
            result['kompass'].append({'id': nid, 'titel': node['fm'].get('title', nid),
                                      'bezug': 'direkt' if nid in direkt else 'Graphverbindung',
                                      'quelle': str(node['pfad'])})
            repo = node['fm'].get('repo')
            if isinstance(repo, str) and Path(repo).expanduser().is_absolute():
                path = Path(repo).expanduser()
                if path.is_dir() and not any(item['repo'] == str(path) for item in result['zugehoerige_repos']):
                    result['zugehoerige_repos'].append({'repo': str(path), 'begruendung': nid,
                        'einstieg': [str(path / name) for name in ('README.md', 'AGENTS.md', 'CLAUDE.md') if (path / name).is_file()]})
    # Fließtext der registrierten Übergaben tatsächlich prüfen; Archive/Vorlagen nicht als Aufträge ausgeben.
    for repo in state.get('repos', []):
        if repo.get('fehler'):
            result['luecken'].append({'repo': repo['pfad'], 'fehler': repo['fehler']})
        for name in repo.get('uebergaben', []):
            path = Path(name)
            if wissen.handoff_kind(path, Path(repo['pfad'])) != 'Übergabe':
                continue
            try:
                if path.is_symlink() or not path.resolve().is_relative_to(Path(repo['pfad']).resolve()):
                    raise ValueError('Quellpfad außerhalb des Repos')
                if path.stat().st_size > 400_000:
                    raise ValueError('Datei für automatische Erschließung zu groß')
                raw = path.read_bytes()
                text = raw.decode('utf-8')
                hits = [{'zeile': i, 'text': line[:350]} for i, line in enumerate(text.splitlines(), 1) if muster.search(line)]
                if hits:
                    result['projektquellen'].append({'repo': repo['pfad'], 'quelle': name,
                        'sha256': wissen.digest(raw), 'ausschnitte': hits[:5],
                        'status': 'thematischer Treffer, keine fachlich abgenommene Aufgabe'})
            except (OSError, ValueError, UnicodeError) as exc:
                result['luecken'].append({'quelle': name, 'fehler': type(exc).__name__})
    gh = state['aufgaben_abgleich']['github']
    for item in gh['items']:
        if muster.search(item['titel'] + ' ' + item['repo'] + ' ' + ' '.join(item['labels'])):
            result['github'].append(item)
    if gh.get('fehler'):
        result['luecken'].append({'quelle': 'GitHub', 'fehler': gh['fehler'], 'letzter_erfolg': gh.get('stand')})
    for key, item in state.get('items', {}).items():
        if item.get('art') == 'repo-uebergabe' or not muster.search(Path(item.get('pfad', '')).name):
            continue
        path = Path(item['pfad'])
        # Dateinamen aus dem alten Register sind Hinweise; Existenz frisch prüfen, nicht als Lektüre zählen.
        result['eingang'].append({'id': key, 'quelle': str(path), 'erreichbar': path.is_file(),
                                  'lesestatus_im_register': item.get('status'), 'inhalt': 'nicht automatisch gelesen'})
    result['gespraeche'] = {'register': str(wissen.STATE), 'umfang': 'Nur gezielte bisherige Fundstellen, kein Vollimport',
                            'quelle': str(root / 'kontextquellen.md')}
    result['luecken'].append({'quelle': 'Abdeckung', 'fehler': 'Worttreffer und Graphbezüge sind Kandidaten; Umformulierungen und übrige Quellen können fehlen. Originale gezielt lesen.'})
    return result


def main(argv):
    thema = ' '.join(argv).strip()
    if not thema:
        print('Nutzung: kompass kontext <Thema> — aktualisiert Quellen beim Aufruf, kein neuer Bericht', file=sys.stderr)
        return 2
    try:
        # Vorwissen zuerst lokal erschließen, dann Originalquellen erneuern und damit zusammenführen.
        kern = lade_kern(wissen.ROOT, vorwissen=True)
        if not kern.begriffe(thema):
            raise ValueError('Kein konkretes Thema')
        kern.suche(thema)
        state = aufgaben.aktualisieren({'immich': immich_zugang()} if wissen.felder(wissen.ROOT).get('immich_url') else {})
        output = erschliessen(thema, state, wissen.ROOT)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1 if state['aufgaben_abgleich']['github'].get('fehler') or state['aufgaben_abgleich'].get('repo_fehler') else 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Kontextabgleich unvollständig ({type(exc).__name__}); kein erfolgreicher Gesamtstand', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
