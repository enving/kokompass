"""Vollständige, versionierte Quellen und verlustfreier Obsidian-Export.

Kein Modellaufruf. Rohdaten liegen außerhalb des OKF-Bundles; Originale bleiben erhalten.
"""
import hashlib
import json
import os
import re
from urllib.parse import quote
from datetime import datetime
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, text):
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def set_fields(text, fields):
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise ValueError("Frontmatter fehlt")
    end = text.index("\n---", 4)
    head, body = text[:end], text[end:]
    for key, value in fields.items():
        line = f"{key}: {value}"
        pattern = rf"(?m)^{re.escape(key)}:.*$"
        head = re.sub(pattern, lambda _: line, head) if re.search(pattern, head) else head + "\n" + line
    return head + body


def source_files(vault):
    """Einziger Eingang: sources. Unterordner werden für Altbestände mitgelesen."""
    result = set()
    for folder in ("sources",):
        root = vault / folder
        if root.exists():
            for p in root.rglob("*"):
                if p.suffix.lower() in (".md", ".mdx", ".txt") and p.is_file() and not p.is_symlink():
                    if not any(x.startswith(".") for x in p.relative_to(root).parts) and p.name not in ("index.md", "README.md", "AGENTS.md"):
                        result.add(p)
    return sorted(result)


def ingest(graph, nodes):
    vault, root = graph.VAULT, graph.ROOT
    if not vault.exists():
        raise FileNotFoundError(f"Vault nicht erreichbar: {vault}")
    storage = Path(os.environ.get("KOMPASS_SOURCES", str(root.parent / "kompass-quellen")))
    by_path = {k["fm"].get("vault_datei"): k for k in nodes.values() if k["ordner"] == "quellen"}
    new = changed = hydrated = 0
    for p in source_files(vault):
        rel = str(p.relative_to(vault))
        # iCloud kann einen Platzhalter als leere Bytes liefern, obwohl stat Inhalt
        # meldet. Niemals dadurch einen vorhandenen Quellstand überschreiben.
        try:
            before = p.stat()
            data = p.read_bytes()
            after = p.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(data) != before.st_size or data != p.read_bytes():
                print(f"eingang: NICHT STABIL LESBAR, unverändert erhalten: {rel}")
                continue
        except OSError:
            print(f"eingang: LESEFEHLER, unverändert erhalten: {rel}")
            continue
        text = data.decode("utf-8-sig")
        sha = digest(data)
        key = digest(rel.encode())[:20]
        snapshot = storage / key / (sha + p.suffix)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if not snapshot.exists():
            with snapshot.open("xb") as f:
                f.write(data)
        if digest(snapshot.read_bytes()) != sha:
            raise ValueError(f"Snapshot beschädigt: {snapshot}")
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        fields = {"source_sha256": sha, "source_snapshot": str(snapshot), "source_bytes": len(data),
                  "source_erfasst": stamp}
        existing = by_path.get(rel)
        if existing:
            old_hash = existing["fm"].get("source_sha256")
            if old_hash == sha:
                continue
            if old_hash:
                fields.update(status="geaendert", vorheriger_status=existing["fm"].get("status", "neu"))
                changed += 1
            else:
                fields["bewertung_version"] = "nicht_protokolliert"
                hydrated += 1
            updated = set_fields(existing["pfad"].read_text(), fields)
            # Nur den eigenen automatisch erzeugten Verweis aktualisieren; frühere Auswertungen erhalten.
            old_snapshot = existing["fm"].get("source_snapshot")
            if old_snapshot:
                updated = updated.replace(f"- Unveränderte Quellversion: `{old_snapshot}`",
                                          f"- Unveränderte Quellversion: `{snapshot}`")
            atomic(existing["pfad"], updated)
            continue
        fm, _ = graph.frontmatter(text)
        title = str(fm.get("title") or p.stem).strip().strip('"').replace("\n", " ")
        url = str(fm.get("source", "")).strip().strip('"')
        stem = graph.slug(title)
        if stem in {"index", "log", "readme", "agents", "claude"}:
            stem = "quelle-" + stem
        target = root / "quellen" / (stem + ".md")
        i = 2
        while target.exists():
            target = root / "quellen" / (stem + f"-{i}.md")
            i += 1
        head = {"type": "Reference", "title": json.dumps(title, ensure_ascii=False),
                "description": "Vollständige Quelle gesichert; inhaltliche Auswertung offen.",
                "vault_datei": rel, "status": "neu", "vertraulich": "ja", "timestamp": stamp, **fields}
        if url.startswith(("https://", "http://")):
            head["resource"] = url
        body = "---\n" + "\n".join(f"{k}: {v}" for k, v in head.items()) + "\n---\n\n"
        body += f"# {title}\n\nErfasst ist der vollständige Text, nicht bereits geprüftes Wissen.\n\n"
        body += "Zur Auswertung den Snapshot vollständig lesen, betroffene Wiki-Seiten aktualisieren, "
        body += "Widersprüche benennen und `ausgewertet_sha256` auf `source_sha256` setzen.\n\n# Citations\n\n"
        body += f"- Original in Obsidian: `{rel}`\n- Unveränderte Quellversion: `{snapshot}`\n"
        atomic(target, body)
        new += 1
    print(f"eingang: {new} neu, {changed} geändert, {hydrated} Volltexte nachgesichert")
    return new + changed + hydrated


def mirror(graph, nodes, hint):
    """Nur selbst erzeugte und unveränderte Abzüge ersetzen; Abweichungen erhalten."""
    root, vault = graph.ROOT, graph.VAULT
    state_path = root / ".zustand" / "spiegel.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    folder = vault / "Kompass/Knoten"
    conflicts = []
    exported = 0
    desired = {}
    for k in nodes.values():
        fm = k["fm"]
        if k["ordner"] not in graph.SPIEGEL_ORDNER or str(fm.get("vertraulich", "")).lower() in ("ja", "true", "yes"):
            continue
        if any(w in k["body"] for w in graph.SPIEGEL_SPERRE):
            continue
        rel = str(k["pfad"].relative_to(root))
        desired[rel] = hint + k["pfad"].read_text()
    for rel, text in desired.items():
        dest = folder / rel
        if dest.exists():
            actual = digest(dest.read_bytes())
            # Beim ersten Lauf nur identische Alt-Abzüge übernehmen.
            if actual != digest(text.encode()) and actual != state.get(rel):
                conflicts.append(rel)
                continue
        atomic(dest, text)
        state[rel] = digest(text.encode())
        exported += 1
    # Keine rekursive Löschung. Nicht mehr exportierbare, bekannte Abzüge lokal sichern.
    retired = root.parent / "kompass-quellen" / "spiegel-archiv"
    for rel in list(state):
        if rel in desired:
            continue
        dest = folder / rel
        if dest.exists():
            if digest(dest.read_bytes()) != state[rel]:
                conflicts.append(rel)
                continue
            saved = retired / (digest(dest.read_bytes())[:16]) / rel
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(dest.read_bytes())
            if saved.read_bytes() != dest.read_bytes():
                raise OSError("Archivprüfung fehlgeschlagen")
            dest.unlink()
        state.pop(rel)
    atomic(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    atomic(root / ".zustand/spiegel-konflikte.json", json.dumps(conflicts, ensure_ascii=False, indent=2) + "\n")
    print(f"spiegel: {exported} Abzüge; {len(conflicts)} Abweichungen unverändert erhalten")
    for rel in conflicts:
        print(f"  KONFLIKT: {rel}")


def source_index(graph, nodes):
    """Nur Quellen auflisten, deren Original bereits im Vault liegt; keine privaten Knoten exportieren."""
    rows = ["---", "type: Index", "title: Quellen und Bearbeitungsstand", "timestamp: " + datetime.now().astimezone().date().isoformat(), "---", "", "# Quellen und Bearbeitungsstand", "",
            "Automatisch erzeugt. **Gesichert ist nicht ausgewertet.** Historische Auswertungen ohne Hash "
            "sind keiner überprüfbaren Quellversion zugeordnet. Originale bleiben unverändert.", "",
            f"[Zum Wiki]({quote(str(graph.VAULT / 'wiki/index.md'), safe='/')}) · Neue Dateien direkt in `sources/` ablegen.", ""]
    groups = {}
    for k in nodes.values():
        rel = k['fm'].get('vault_datei')
        if not isinstance(rel, str):
            continue
        path = graph.VAULT / rel
        if not path.is_file() or not path.resolve().is_relative_to(graph.VAULT.resolve()):
            continue
        group = str(Path(rel).parent)
        groups.setdefault(group, []).append(k)
    for group, items in sorted(groups.items()):
        rows += [f"## {group}", "", "| Quelle | Bearbeitungsstand |", "|---|---|"]
        for k in sorted(items, key=lambda x: x['fm'].get('title', '')):
            fm = k['fm']
            title = str(fm.get('title', k['pfad'].stem)).strip('"').replace('|', '–').replace('[', '').replace(']', '')
            status = fm.get('status', 'offen')
            if fm.get('source_sha256') and fm.get('ausgewertet_sha256') == fm['source_sha256']:
                status = 'Teilquelle bewertet; Umfang beachten' if status == 'teilquelle' else 'ausgewertet; Version belegt'
            elif status == 'ausgewertet':
                status = 'historisch ausgewertet; Versionsbezug fehlt'
            elif status == 'neu':
                status = 'Volltext gesichert; Auswertung offen'
            target = quote(str(graph.VAULT / fm['vault_datei']), safe='/')
            rows.append(f"| [{title}]({target}) | {status} |")
        rows.append('')
    atomic(graph.ROOT / 'berichte/quellen.md', '\n'.join(rows))
