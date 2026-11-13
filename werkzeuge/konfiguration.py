"""Instanzwerte aus dem bestehenden Quellenregister, ohne Rechner-Voreinstellungen."""
import importlib.util
import os
from pathlib import Path


def wurzel():
    return Path(os.environ.get('KOMPASS_DIR') or Path.cwd()).expanduser().resolve()


def felder(root=None):
    path = (root or wurzel()) / 'kontextquellen.md'
    if not path.is_file():
        return {}
    spec = importlib.util.spec_from_file_location('kompass_parser', Path(__file__).with_name('kompass.py'))
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core.frontmatter(path.read_text(encoding='utf-8'))[0]


def pfad(value, root=None):
    root = root or wurzel()
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def vault_pfad(root=None):
    value = os.environ.get('KOMPASS_VAULT') or felder(root).get('vault_pfad')
    return pfad(value, root) if value else None


def lokaler_repo_pfad(value, root=None):
    if not isinstance(value, str) or not value or value.startswith(
            ('https://', 'http://', 'ssh://', 'git://', 'git@', 'github.com/')):
        return None
    return pfad(value, root)
