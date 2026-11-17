import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_dir = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.config_dir.cleanup()

    def run_cli(self, *args, input_text=None):
        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = self.config_dir.name
        return subprocess.run(
            [sys.executable, "-m", "pythonator", *args],
            cwd=ROOT,
            env=env,
            text=True,
            input=input_text,
            capture_output=True,
            check=False,
            timeout=20,
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

    def test_complex_json(self):
        result = self.run_cli("--json", "--eval", "1+2i")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], {"real": 1.0, "imag": 2.0})

    def test_error(self):
        result = self.run_cli("--eval", "1/0")
        self.assertEqual(result.returncode, 0)
        self.assertIn("division by zero", result.stdout)
        result = self.run_cli("--no-such-option")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option", result.stderr)

    def test_repl_rejects_non_finite_command_arguments(self):
        result = self.run_cli(input_text="primes 1e999\nfactorize 1e999\nq\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("primes [n]", result.stdout)
        self.assertIn("factorize <n>", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

if __name__ == "__main__":
    unittest.main()
