import math
import unittest

from pythonator.engine import Context, EngineError, eval_statements, format_number, format_value, parse_expression, eval_node, format_ast
from pythonator.__main__ import parse_plot_spec, parse_table_spec

class EngineTests(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(self.evaluate("2+3*4"), 14)
        self.assertEqual(self.evaluate("(2+3)*4"), 20)
        self.assertEqual(self.evaluate("-2^2"), -4)
        self.assertEqual(self.evaluate("2^3^2"), 512)

    def test_percent_and_factorial(self):
        self.assertEqual(self.evaluate("200+10%"), 220)
        self.assertEqual(self.evaluate("5!"), 120)
        self.assertEqual(self.evaluate("fact(6)"), 720)

    def test_variables_and_implicit_multiplication(self):
        self.assertEqual(self.evaluate("x=4; 2x"), 8)
        self.assertEqual(self.evaluate("y=3; y(2+1)"), 9)

    def test_user_functions(self):
        self.assertEqual(self.evaluate("f(x)=x^2+1; f(3)"), 10)
        self.assertEqual(self.evaluate("g(x, y)=x+y; g(2, 3)"), 5)

    def test_functions(self):
        self.assertEqual(self.evaluate("sqrt(16)"), 4)
        self.assertEqual(self.evaluate("min(3, 1, 2)"), 1)
        self.assertEqual(self.evaluate("max(3, 1, 2)"), 3)
        self.assertEqual(self.evaluate("clamp(8, 0, 5)"), 5)
        self.assertEqual(self.evaluate("isprime(7)"), 1)
        self.assertEqual(self.evaluate("isprime(8)"), 0)
        self.assertEqual(self.evaluate("ncr(5, 2)"), 10)
        with self.assertRaises(EngineError):
            self.evaluate("ncr(1e20, 1000000)")
        with self.assertRaises(EngineError):
            self.evaluate("npr(1e9, 1000000)")
        root = self.evaluate("(-8)^0.5")
        self.assertAlmostEqual(root.real, 0, places=12)
        self.assertAlmostEqual(root.imag, math.sqrt(8), places=12)
        root = self.evaluate("pow(-8, 0.5)")
        self.assertAlmostEqual(root.real, 0, places=12)
        self.assertAlmostEqual(root.imag, math.sqrt(8), places=12)
        with self.assertRaises(EngineError):
            self.evaluate("pow(0, -1)")

    def test_constants(self):
        self.assertAlmostEqual(self.evaluate("pi*2"), 6.283185307179586, places=12)

    def test_unknown_variable(self):
        with self.assertRaises(Exception):
            self.evaluate("no_such_variable")

    def test_reset_preserves_settings_and_memory(self):
        ctx = Context()
        ctx.radix = 16
        ctx.memory = 42.0
        ctx.has_memory = True
        ctx.set_var("x", 9)
        ctx.reset()
        assert ctx.radix == 16
        assert ctx.memory == 42.0
        assert ctx.has_memory is True
        assert "x" not in ctx.vars

    def test_plot_spec(self):
        funcs, low, high = parse_plot_spec("sin(x), cos(x) -6.28 6.28")
        self.assertEqual(funcs, ["sin(x)", "cos(x)"])
        self.assertEqual((low, high), (-6.28, 6.28))
        funcs, low, high = parse_plot_spec("sin(x)")
        self.assertEqual(funcs, ["sin(x)"])
        self.assertEqual((low, high), (-10.0, 10.0))
        funcs, low, high = parse_plot_spec("max(x, 0)")
        self.assertEqual(funcs, ["max(x, 0)"])
        self.assertEqual((low, high), (-10.0, 10.0))
        funcs, low, high = parse_plot_spec("x + 1")
        self.assertEqual(funcs, ["x + 1"])
        self.assertEqual((low, high), (-10.0, 10.0))
        expression, low, high = parse_table_spec("x^2 -5 5")
        self.assertEqual((expression, low, high), ("x^2", -5.0, 5.0))
        expression, low, high = parse_table_spec("x + 1")
        self.assertEqual((expression, low, high), ("x + 1", -10.0, 10.0))

    def test_explain_tree(self):
        tree = format_ast(parse_expression("2+3*4"))
        self.assertIn("Binary +", tree)
        self.assertIn("Binary *", tree)
        self.assertEqual(tree.count("Binary"), 2)
        self.assertIn("Num 4", tree)

    def test_complex_numbers(self):
        self.assertEqual(self.evaluate("i*i"), -1)
        self.assertEqual(self.evaluate("sqrt(-1)"), 1j)
        self.assertEqual(self.evaluate("abs(3+4i)"), 5)
        self.assertAlmostEqual(self.evaluate("arg(i)"), math.pi / 2, places=12)
        self.assertEqual(self.evaluate("conj(2+3i)"), 2 - 3j)
        self.assertEqual(self.evaluate("re(2+3i)"), 2)
        self.assertEqual(self.evaluate("im(2+3i)"), 3)

    def test_real_valued_complex_arguments_to_builtins(self):
        self.assertAlmostEqual(self.evaluate("cbrt(i*i)"), -1)
        self.assertAlmostEqual(self.evaluate("sin(i*i)"), -0.8414709848078965, places=12)
        self.assertAlmostEqual(self.evaluate("exp(i*i)"), math.exp(-1), places=12)
        self.assertAlmostEqual(self.evaluate("atan(i*i)"), -math.pi / 4, places=12)
        self.assertAlmostEqual(self.evaluate("asin(i*i)"), -math.pi / 2, places=12)
        self.assertEqual(self.evaluate("round(i*i)"), -1)
        with self.assertRaises(EngineError):
            self.evaluate("log(i*i)")
        with self.assertRaises(EngineError):
            self.evaluate("asin(2+0i)")
        with self.assertRaises(EngineError):
            self.evaluate("atan(i)")
        with self.assertRaises(EngineError):
            self.evaluate("mod(3.5, 1e-308)")

    def test_radix_formatting(self):
        self.assertEqual(format_value(255, 16), "0xff")
        self.assertEqual(format_value(5, 2), "0b101")
        self.assertEqual(format_value(-10, 16), "-0xa")
        self.assertIn("e", format_value(1234, 0))
        self.assertEqual(format_value(1234.5, 16), "1234.5")

    def evaluate(self, text):
        ctx = Context()
        results = eval_statements(text, ctx)
        for value in reversed(results):
            if value is not None:
                return value
        self.fail("no result")

if __name__ == "__main__":
    unittest.main()
