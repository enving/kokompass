#!/usr/bin/env python3
"""Kompatibler Aufruf für bestehende Hooks; die Suche läuft vollständig im Kokompass-Kern."""
import os
from pathlib import Path
import sys
from kern_adapter import INSTANZ, lade_kern


def main(argv):
    try:
        wurzel = Path(os.environ.get("KOMPASS_DIR") or INSTANZ)
        return lade_kern(wurzel, vorwissen=True).vorwissen(argv)
    except (OSError, RuntimeError) as error:
        if "--auto" not in argv:
            print(f"vorwissen: {error}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
