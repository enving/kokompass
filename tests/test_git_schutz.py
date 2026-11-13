import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "werkzeuge"))
import json
import subprocess
import unittest
from unittest.mock import patch

import git_schutz


class PushSchutzTest(unittest.TestCase):
    def setUp(self):
        self.setting = patch.object(git_schutz, 'REPOSITORY', 'beispiel/privater-kompass')
        self.setting.start()
        self.addCleanup(self.setting.stop)

    refs = "refs/heads/master " + "a" * 40 + " refs/heads/master " + "0" * 40 + "\n"

    def test_oeffentliche_vorlage_und_fremde_ziele_gesperrt(self):
        with patch.object(git_schutz, "run") as run:
            for url in ["https://github.com/beispiel/vorlage.git",
                        "https://github.com/beispiel/privater-kompass.git/anders",
                        "https://github.com/anders/kompass.git"]:
                with self.assertRaises(ValueError):
                    git_schutz.pruefen(url, self.refs)
            run.assert_not_called()

    def test_sichtbarkeit_forkstatus_und_identitaet_muessen_stimmen(self):
        for info in [{"full_name": "beispiel/privater-kompass", "private": False, "fork": False},
                     {"full_name": "beispiel/privater-kompass", "private": True, "fork": True},
                     {"full_name": "anders/kompass", "private": True, "fork": False}, {}]:
            with patch.object(git_schutz, "run", return_value=subprocess.CompletedProcess(
                    [], 0, stdout=json.dumps(info))) as run:
                with self.assertRaises(ValueError):
                    git_schutz.pruefen("https://github.com/beispiel/privater-kompass.git", self.refs)
                self.assertEqual(run.call_count, 1)

    def test_geheimnisfund_oder_netzfehler_verhindert_push(self):
        info = subprocess.CompletedProcess([], 0, stdout=json.dumps(
            {"full_name": "beispiel/privater-kompass", "private": True, "fork": False}))
        with patch.object(git_schutz, "run", side_effect=[info, subprocess.CalledProcessError(1, "gitleaks")]):
            with self.assertRaises(subprocess.CalledProcessError):
                git_schutz.pruefen("https://github.com/beispiel/privater-kompass.git", self.refs)
        with patch.object(git_schutz, "run", side_effect=OSError("offline")):
            with self.assertRaises(OSError):
                git_schutz.pruefen("https://github.com/beispiel/privater-kompass.git", self.refs)

    def test_erlaubtes_ziel_prueft_gesamte_ausgehende_historie(self):
        info = subprocess.CompletedProcess([], 0, stdout=json.dumps(
            {"full_name": "beispiel/privater-kompass", "private": True, "fork": False}))
        with patch.object(git_schutz, "run", return_value=info) as run:
            git_schutz.pruefen("git@github.com:beispiel/privater-kompass.git", self.refs)
            self.assertEqual(run.call_count, 2)
            command = run.call_args.args[0]
            self.assertEqual(command[:2], ["gitleaks", "git"])
            self.assertIn("--log-opts=" + "a" * 40, command)
            self.assertIn("--redact", command)


if __name__ == "__main__":
    unittest.main()
