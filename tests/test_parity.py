import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUSALATOR = pathlib.Path(
    os.environ.get("PLUSALATOR_BIN", ROOT.parent / "Plusalator" / "plusalator")
)

CASES = (
    ("2+3*4", 14.0),
    ("(2+3)*4", 20.0),
    ("2^3^2", 512.0),
    ("-2^2", -4.0),
    ("sqrt(2)", 1.4142135623730951),
    ("pi*2", 6.283185307179586),
    ("2(3+4)", 14.0),
    ("(2+3)(4+5)", 45.0),
    ("2sin(pi/2)", 2.0),
    ("f(x)=x^2+1;f(3)", 10.0),
    ("200+10%", 220.0),
    ("5!", 120.0),
    ("0x10", 16.0),
    ("floor(2.9)", 2.0),
    ("abs(-5)", 5.0),
    ("mod(10,3)", 1.0),
    ("cbrt(-8)", -2.0),
    ("gcd(12,18)", 6.0),
    ("lcm(4,6)", 12.0),
    ("clamp(9,3,7)", 7.0),
)


def evaluate(command, expression, home):
    env = os.environ.copy()
    env.update({"HOME": home, "XDG_CONFIG_HOME": home, "NO_COLOR": "1", "TMPDIR": home})
    env.pop("FORCE_COLOR", None)
    args = [*command, f"--eval={expression}"] if command[0] == sys.executable else [*command, "--eval", expression]
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        raise AssertionError(f"{' '.join(command)} {expression!r} exited {result.returncode}: {result.stderr.strip()}")
    return float(result.stdout.strip())


class ParityTests(unittest.TestCase):
    def test_pythonator_matches_shared_cases(self):
        with tempfile.TemporaryDirectory() as home:
            for expression, expected in CASES:
                with self.subTest(expression=expression):
                    got = evaluate([sys.executable, "-m", "pythonator"], expression, home)
                    self.assertAlmostEqual(got, expected, places=9)

                    if PLUSALATOR.is_file() and os.access(PLUSALATOR, os.X_OK):
                        other = evaluate([str(PLUSALATOR)], expression, home)
                        self.assertAlmostEqual(other, expected, places=9)
                        self.assertAlmostEqual(got, other, places=9)


if __name__ == "__main__":
    unittest.main()
