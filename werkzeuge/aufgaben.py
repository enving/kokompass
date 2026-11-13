#!/usr/bin/env python3
"""Lesender Quellenabgleich im vorhandenen Eingangsregister; kein eigener Aufgabenbericht."""
import json
import re
import subprocess
import sys

from eingang import atomic
import wissen


def github_owner(root):
    result = subprocess.run(['git', '-C', str(root), 'remote', 'get-url', 'origin'],
                            capture_output=True, text=True, timeout=10, check=True)
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([\w-]+)/[\w.-]+(?:\.git)?', result.stdout.strip())
    if not match:
        raise ValueError('GitHub-Eigentümer aus origin nicht eindeutig; keine breite Ersatzsuche')
    return match[1]


def github_lesen(owner):
    result = subprocess.run(['gh', 'api', '--method', 'GET', 'search/issues', '-f',
                             f'q=is:open user:{owner}', '-f', 'per_page=100', '--paginate', '--slurp'],
                            capture_output=True, text=True, timeout=90, check=True)
    pages = json.loads(result.stdout)
    if not isinstance(pages, list) or not pages:
        raise ValueError('GitHub lieferte keine prüfbare Suchantwort')
    totals = {page['total_count'] for page in pages}
    if len(totals) != 1 or any(page.get('incomplete_results', True) for page in pages):
        raise ValueError('GitHub-Suche unvollständig oder während des Abrufs verändert')
    items = {}
    for page in pages:
        for item in page['items']:
            url = item['html_url']
            match = re.fullmatch(r'https://github\.com/([^/]+/[^/]+)/(issues|pull)/\d+', url)
            if not match or match[1].split('/')[0].casefold() != owner.casefold() or item['state'] != 'open':
                raise ValueError('GitHub-Ergebnis außerhalb der gewählten offenen Quellen')
            items[url] = {'url': url, 'repo': match[1], 'nummer': item['number'], 'titel': item['title'],
                          'art': 'PR' if 'pull_request' in item else 'Issue', 'status': item['state'],
                          'labels': [label['name'] for label in item['labels']],
                          'zugewiesen': [person['login'] for person in item['assignees']],
                          'aktualisiert': item['updated_at']}
    if len(items) != next(iter(totals)):
        raise ValueError('GitHub-Suchlimit oder fehlende Ergebnisseite; kein vollständiger Abgleich')
    return sorted(items.values(), key=lambda item: (item['repo'].casefold(), item['art'], item['nummer']))


def github_abgleichen(state, owner):
    prior = state.get('aufgaben_abgleich', {}).get('github', {})
    try:
        items = github_lesen(owner)
        old = {item['url']: item for item in prior.get('items', [])} if prior.get('owner') == owner else {}
        new = {item['url']: item for item in items}
        return {'owner': owner, 'versuch': wissen.stamp(), 'stand': wissen.stamp(),
                'fehler': None, 'items': items, 'vorheriger_stand': prior.get('stand') if prior.get('owner') == owner else None,
                'neu': sorted(new.keys() - old.keys()), 'nicht_mehr_offen': sorted(old.keys() - new.keys()),
                'geaendert': sorted(url for url in old.keys() & new.keys() if old[url] != new[url])}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        # Keine rohe CLI-Ausgabe: sie kann Verbindungs- oder Zugangsinformationen enthalten.
        old = prior if prior.get('owner') == owner else {}
        return {**old, 'owner': owner, 'versuch': wissen.stamp(),
                'fehler': 'GitHub-Abruf fehlgeschlagen/unvollständig; letzten erfolgreichen Stand erhalten',
                'items': old.get('items', [])}


def aktualisieren(zugaenge=None):
    wissen.scan()
    handoff_error = wissen.handoffs()
    raw = wissen.STATE.read_bytes()
    state = json.loads(raw)
    config = wissen.felder(wissen.ROOT)
    gh = {'items': [], 'stand': None, 'fehler': None, 'aktiv': False}
    if str(config.get('github_aktiv', '')).casefold() in {'ja', 'true'}:
        gh = github_abgleichen(state, github_owner(wissen.ROOT))
    state['aufgaben_abgleich'] = {'stand': wissen.stamp(), 'github': gh}
    if zugaenge is not None:
        state['kontext_zugaenge'] = zugaenge
    state['aufgaben_abgleich']['repo_fehler'] = handoff_error
    if wissen.STATE.read_bytes() != raw:
        raise RuntimeError('Eingangsregister zwischenzeitlich geändert; nicht überschrieben')
    atomic(wissen.STATE, json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    return state


if __name__ == '__main__':
    from kontext import main
    sys.exit(main(sys.argv[1:] or ['offene Aufgaben']))
