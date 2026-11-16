import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "pythonator", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_eval(self):
        result = self.run_cli("--eval", "2+3*4")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "14")

    def test_json(self):
        result = self.run_cli("--json", "--eval", "sqrt(16)")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["expression"], "sqrt(16)")
        self.assertEqual(payload["result"], 4.0)

    def test_error(self):
        result = self.run_cli("--eval", "1/0")
        self.assertEqual(result.returncode, 0)
        self.assertIn("division by zero", result.stderr)

if __name__ == "__main__":
    unittest.main()
