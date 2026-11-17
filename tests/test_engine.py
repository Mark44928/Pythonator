import unittest

from pythonator.engine import Context, eval_statements, format_number, format_value, parse_expression, eval_node, format_ast
from pythonator.__main__ import parse_plot_spec

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

    def test_explain_tree(self):
        tree = format_ast(parse_expression("2+3*4"))
        self.assertIn("Binary +", tree)
        self.assertIn("Binary *", tree)
        self.assertEqual(tree.count("Binary"), 2)
        self.assertIn("Num 4", tree)

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
