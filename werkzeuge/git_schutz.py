#!/usr/bin/env python3
"""Lokaler Push-Schutz einer privaten Kompass-Instanz; Einrichtung mit 'installieren'."""
import json
from pathlib import Path
import re
import subprocess
import sys

from konfiguration import wurzel, felder

ROOT = wurzel()
REPOSITORY = felder(ROOT).get("privates_git_repo", "")


def erlaubt(url):
    return bool(REPOSITORY) and url in {
        f"https://github.com/{REPOSITORY}",
        f"https://github.com/{REPOSITORY}.git",
        f"git@github.com:{REPOSITORY}.git",
        f"ssh://git@github.com/{REPOSITORY}.git",
    }


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def pruefen(url, refs):
    if not erlaubt(url):
        raise ValueError("Push gesperrt: Ziel ist nicht das freigegebene private Kompass-Repo.")
    info = json.loads(run(["gh", "api", f"repos/{REPOSITORY}"],
                          capture_output=True, text=True, timeout=30).stdout)
    if info.get("full_name") != REPOSITORY or info.get("private") is not True or info.get("fork") is not False:
        raise ValueError("Push gesperrt: Ziel ist nicht als eigenständiges privates Repo bestätigt.")
    commits = set()
    for line in refs.splitlines():
        fields = line.split()
        if len(fields) != 4:
            raise ValueError("Push gesperrt: ungültige Git-Referenz.")
        sha = fields[1]
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha):
            raise ValueError("Push gesperrt: ungültige Objektkennung.")
        if set(sha) != {"0"}:
            commits.add(sha)
    for sha in sorted(commits):
        run(["gitleaks", "git", str(ROOT), f"--log-opts={sha}", "--redact", "--no-banner"], timeout=120)


def installieren():
    if not REPOSITORY:
        raise ValueError("privates_git_repo in kontextquellen.md fehlt; keine Hooks verändert.")
    config = subprocess.run(["git", "config", "--get", "core.hooksPath"],
                            cwd=ROOT, capture_output=True, text=True, timeout=10)
    if config.returncode not in {0, 1}:
        config.check_returncode()
    current = config.stdout.strip()
    if current not in {"", ".githooks"}:
        raise ValueError("Vorhandener hooksPath bleibt erhalten; Push-Schutz dort einbinden.")
    native = run(["git", "rev-parse", "--git-path", "hooks/pre-push"],
                 capture_output=True, text=True).stdout.strip()
    if not current and (ROOT / native).exists():
        raise ValueError("Vorhandener pre-push-Hook bleibt erhalten; Schutz zuerst zusammenführen.")
    run(["git", "config", "core.hooksPath", ".githooks"])
    run(["git", "config", "remote.pushDefault", "origin"])
    run(["git", "config", "push.default", "simple"])
    run(["git", "config", "push.recurseSubmodules", "no"])
    if (ROOT / "kern" / ".git").exists():
        run(["git", "-C", "kern", "config", "remote.origin.pushurl", "DISABLED"])
    print("Lokaler Push-Schutz installiert; Vorlagen-Remote nur zum Lesen eingerichtet.")


def main():
    try:
        if sys.argv[1:] == ["installieren"]:
            installieren()
        elif len(sys.argv) == 3:
            pruefen(sys.argv[2], sys.stdin.read())
        else:
            raise ValueError("Aufruf: git_schutz.py installieren oder als pre-push-Hook.")
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Kompass-Push abgebrochen: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
