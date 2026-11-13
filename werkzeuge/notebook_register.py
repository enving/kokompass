#!/usr/bin/env python3
"""Notebook-Beobachtungen vergleichen, ohne LLM, Netz oder Zugriff auf Anmeldedaten.

Ein autorisierter Browser-Agent liefert ein vollständiges JSON-Inventar. Ein
erfolgreicher Vergleich ist kein Beweis, dass die Inhalte bereits gelesen sind.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import os
from eingang import atomic
from konfiguration import wurzel, felder

ROOT = wurzel()
STATE = ROOT / '.zustand/notebooklm'
NOTEBOOK = felder(ROOT).get('notebook_id', '')


def reconcile(inventory):
    if not NOTEBOOK or inventory.get('notebook_id') != NOTEBOOK or inventory.get('complete') is not True:
        raise ValueError('Notebook-ID oder bestätigtes vollständiges Inventar fehlt')
    if not isinstance(inventory.get('items'), list):
        raise ValueError('Inventarliste fehlt')
    current = {}
    for item in inventory['items']:
        if not all(isinstance(item.get(k), str) and item[k] for k in ('id', 'title', 'kind')):
            raise ValueError('Jedes Element benötigt stabile ID, Titel und Art')
        if item['id'] in current:
            raise ValueError('Doppelte Inventar-ID')
        current[item['id']] = {k: item.get(k) for k in ('id', 'title', 'kind', 'version', 'content_sha256')}
    target = STATE / 'inventory.json'
    previous = json.loads(target.read_text())['items'] if target.exists() else {}
    changes = {'neu': [], 'geaendert': [], 'unveraendert': [], 'entfernt': [], 'version_unbekannt': []}
    for key, item in current.items():
        if key not in previous:
            changes['neu'].append(key)
        elif previous[key] != item:
            changes['geaendert'].append(key)
        elif not item['version'] and not item['content_sha256']:
            changes['version_unbekannt'].append(key)
        else:
            changes['unveraendert'].append(key)
    changes['entfernt'] = sorted(set(previous) - set(current))
    stamp = datetime.now().astimezone().isoformat(timespec='seconds')
    state = {'notebook_id': NOTEBOOK, 'checked': stamp, 'items': current, 'changes': changes,
             'hinweis': 'Ohne Versionsmerkmal lässt sich Inhaltsänderung nicht ausschließen. Keine Löschung lokaler Quellen.'}
    if target.exists():
        old = target.read_bytes()
        backup = STATE / 'history' / (hashlib.sha256(old).hexdigest() + '.json')
        if not backup.exists():
            atomic(backup, old.decode())
    atomic(target, json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    return changes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path, help='JSON aus tatsächlich gelesener Browseransicht')
    args = parser.parse_args()
    print(json.dumps(reconcile(json.loads(args.inventory.read_text())), ensure_ascii=False, indent=2))
