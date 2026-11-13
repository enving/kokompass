"""Repo-Wegweiser und lesende Einrichtungsprüfung; keine Reparatur oder Netzwerkzugriffe."""
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

from konfiguration import wurzel, felder, pfad, vault_pfad
from kern_adapter import lade_kern
import wissen


def repos():
    beschreibung = {}
    for node in lade_kern(wissen.ROOT).laden().values():
        value = node['fm'].get('repo')
        if isinstance(value, str) and value and not value.startswith(('https://', 'http://', 'git@')):
            beschreibung[str(pfad(value, wissen.ROOT))] = node['fm'].get('description') or node['fm'].get('title')
    result = []
    for repo in wissen.repo_paths():
        item = {'pfad': str(repo), 'zweck': beschreibung.get(str(repo), 'nicht beschrieben'),
                'einstieg': [str(repo / name) for name in ('AGENTS.md', 'CLAUDE.md', 'README.md') if (repo / name).is_file()],
                'hinweis': 'Navigation ist keine Arbeitsfreigabe; Auftrag und Repo-Regeln lesen.'}
        if not (repo / '.git').exists():
            item['fehler'] = 'Repo fehlt oder ist kein Git-Arbeitsbaum'
        else:
            try:
                out = subprocess.run(['git', '-C', str(repo), 'remote', 'get-url', 'origin'],
                                     capture_output=True, text=True, timeout=5)
                remote = out.stdout.strip()
                # Keine eingebetteten Anmeldedaten aus Git-URLs ausgeben.
                if out.returncode == 0:
                    if remote.startswith(('https://', 'http://')):
                        parsed = urlsplit(remote)
                        remote = f'{parsed.scheme}://{parsed.hostname}{parsed.path}'
                    item['remote'] = remote
                item['uebergaben'] = [str(p) for p in wissen.handoff_files(repo)]
            except (OSError, subprocess.SubprocessError, ValueError, RuntimeError):
                item['fehler'] = 'Repo-Metadaten nicht lesbar'
        result.append(item)
    return result


def diagnose():
    root = wurzel()
    checks = []
    for name in ('person/ich.md', 'person/ziele.md', 'AGENTS.md', 'kontextquellen.md'):
        checks.append({'quelle': name, 'ok': (root / name).is_file(), 'pflicht': True})
    vault = vault_pfad(root)
    if vault is not None:
        checks.append({'quelle': 'vault_pfad', 'ok': vault.is_dir(), 'pflicht': True})
    config = felder(root)
    for key in ('stt_api_pfad', 'okf_pruefer'):
        if config.get(key):
            checks.append({'quelle': key, 'ok': pfad(config[key], root).exists(), 'pflicht': False})
    for item in repos():
        checks.append({'quelle': item['pfad'], 'ok': 'fehler' not in item,
                       'pflicht': True, 'hinweis': item.get('fehler')})
    return {'pruefungen': checks, 'fehler': sum(not x['ok'] and x['pflicht'] for x in checks),
            'hinweis': 'Dateien und Verweise lokal geprüft. Keine Installation, Anmeldung oder Host-Automation geprüft.'}


def main(argv):
    if argv == ['repos']:
        result = repos()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if any('fehler' in x for x in result) else 0
    if argv == ['diagnose']:
        result = diagnose()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result['fehler'] else 0
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
