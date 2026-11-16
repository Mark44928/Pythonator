import math
import re
from dataclasses import dataclass

class EngineError(Exception):
    pass

@dataclass(frozen=True)
class Num:
    value: float

@dataclass(frozen=True)
class Var:
    name: str

@dataclass(frozen=True)
class Unary:
    op: str
    expr: object

@dataclass(frozen=True)
class Binary:
    op: str
    left: object
    right: object

@dataclass(frozen=True)
class Call:
    name: str
    args: tuple

NUMBER = re.compile(r"0x[0-9a-fA-F_]+|0b[01_]+|0o[0-7_]+|(?:\d[\d_]*(?:\.[\d_]*)?|\.\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?")
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
OPS = "+-*/^%!(),="

def tokenize(text):
    out = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        for kind, pattern in (("number", NUMBER), ("name", NAME)):
            match = pattern.match(text, i)
            if match:
                out.append((kind, match.group(0)))
                i = match.end()
                break
        else:
            if text[i] in OPS:
                out.append(("op", text[i]))
                i += 1
            else:
                raise EngineError(f"unexpected character {text[i]!r}")
    return out

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self):
        token = self.peek()
        self.pos += 1
        return token

    def parse(self):
        if not self.tokens:
            raise EngineError("empty expression")
        node = self.parse_expression(0)
        if self.peek() is not None:
            kind, value = self.peek()
            raise EngineError(f"unexpected token {value!r}")
        return node

    def parse_expression(self, rbp):
        token = self.peek()
        if token is None:
            raise EngineError("unexpected end of expression")
        node = self.nud(token)
        while True:
            token = self.peek()
            if token is None:
                break
            kind, value = token
            if kind == "op" and value in "!%":
                if 35 <= rbp:
                    break
                self.advance()
                node = Unary(value, node)
                continue
            implicit = kind in ("number", "name") or (kind == "op" and value == "(")
            if implicit:
                lbp = 20
            elif kind == "op" and value in "+-*/^":
                lbp = {"+" : 10, "-" : 10, "*" : 20, "/" : 20, "^" : 30}[value]
            else:
                break
            if lbp <= rbp:
                break
            if not implicit:
                self.advance()
            if implicit:
                node = Binary("*", node, self.parse_expression(lbp + 1))
            else:
                rhs_rbp = lbp - 1 if value == "^" else lbp + 1
                node = Binary(value, node, self.parse_expression(rhs_rbp))
        return node

    def nud(self, token):
        kind, value = token
        if kind == "number":
            self.advance()
            return Num(parse_number(value))
        if kind == "name":
            self.advance()
            if self.peek() and self.peek() == ("op", "("):
                self.advance()
                args = []
                if not (self.peek() and self.peek() == ("op", ")")):
                    while True:
                        args.append(self.parse_expression(0))
                        if self.peek() == ("op", ","):
                            self.advance()
                            continue
                        break
                if not self.peek() or self.peek() != ("op", ")"):
                    raise EngineError("missing )")
                self.advance()
                return Call(value.lower(), tuple(args))
            return Var(value)
        if kind == "op":
            if value == "(":
                self.advance()
                node = self.parse_expression(0)
                if not self.peek() or self.peek() != ("op", ")"):
                    raise EngineError("missing )")
                self.advance()
                return node
            if value == "-":
                self.advance()
                return Unary("-", self.parse_expression(15))
            if value == "+":
                self.advance()
                return self.parse_expression(15)
        raise EngineError(f"unexpected token {value!r}")

def parse_number(text):
    cleaned = text.replace("_", "")
    try:
        if cleaned.startswith("0x"):
            return float(int(cleaned, 16))
        if cleaned.startswith("0b"):
            return float(int(cleaned, 2))
        if cleaned.startswith("0o"):
            return float(int(cleaned, 8))
        return float(cleaned)
    except ValueError as exc:
        raise EngineError(f"invalid number {text!r}") from exc

CONSTANTS = {
    "pi": math.pi,
    "tau": math.tau,
    "phi": (1 + math.sqrt(5)) / 2,
    "grav": 9.80665,
    "G": 6.67430e-11,
    "kB": 1.380649e-23,
    "R": 8.314462618,
    "NA": 6.02214076e23,
    "c": 299792458.0,
    "h": 6.62607015e-34,
    "hbar": 1.054571817e-34,
    "sigma": 5.670374419e-8,
    "eps0": 8.8541878128e-12,
    "mu0": 1.25663706212e-6,
    "u": 1.66053906660e-27,
    "m_e": 9.1093837015e-31,
    "m_p": 1.67262192369e-27,
    "e": math.e,
}
BUILTIN_FUNCTIONS = {
    "sqrt", "cbrt", "sin", "cos", "tan", "asin", "acos", "atan",
    "asinh", "acosh", "atanh", "log", "log2", "ln", "exp", "abs",
    "floor", "ceil", "round", "sign", "isprime", "nextprime", "prevprime",
    "min", "max", "clamp", "gcd", "lcm", "pow", "mod", "hypot",
    "ncr", "npr", "fact",
}
RESERVED = set(CONSTANTS) | BUILTIN_FUNCTIONS | {"ans"}

def is_prime(number):
    if number > 1e12:
        raise EngineError("isprime out of range")
    n = int(math.floor(abs(number)))
    if n < 2:
        return 0.0
    if n == 2:
        return 1.0
    if n % 2 == 0:
        return 0.0
    d = 3
    while d <= n // d:
        if n % d == 0:
            return 0.0
        d += 2
    return 1.0

def next_prime(number):
    if number > 1e12:
        raise EngineError("nextprime out of range")
    n = int(math.floor(abs(number))) + 1
    if n <= 2:
        return 2.0
    if n % 2 == 0:
        n += 1
    while not is_prime(n):
        n += 2
        if n > 1e12:
            raise EngineError("nextprime out of range")
    return float(n)

def prev_prime(number):
    if number > 1e12:
        raise EngineError("prevprime out of range")
    n = int(math.ceil(abs(number))) - 1
    if n < 2:
        raise EngineError("prevprime: no prime strictly before argument")
    if n == 2:
        return 2.0
    if n % 2 == 0:
        n -= 1
    while not is_prime(n):
        n -= 2
        if n < 2:
            raise EngineError("prevprime: no prime strictly before argument")
    return float(n)

class Context:
    def __init__(self):
        self.vars = dict(CONSTANTS)
        self.vars["ans"] = 0.0
        self.functions = {}
        self.angle = "rad"
        self.depth = 0

    def reset(self):
        self.vars = dict(CONSTANTS)
        self.vars["ans"] = 0.0
        self.functions = {}
        self.depth = 0

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        raise EngineError(f"unknown variable {name!r}")

    def set_var(self, name, value):
        if name in CONSTANTS:
            raise EngineError(f"{name} is a built-in constant")
        if name in BUILTIN_FUNCTIONS:
            raise EngineError(f"{name} is a built-in function")
        self.vars[name] = value

    def set_function(self, name, params, body):
        if name in CONSTANTS:
            raise EngineError(f"{name} is a built-in constant")
        if name in BUILTIN_FUNCTIONS:
            raise EngineError(f"{name} is a built-in function")
        self.functions[name] = (params, body)

def factorial(value):
    if not math.isfinite(value) or value < 0 or value > 170:
        return math.nan if value < 0 or not math.isfinite(value) else math.inf
    n = int(math.floor(value))
    result = 1
    for item in range(2, n + 1):
        result *= item
    return float(result)

def to_angle(value, mode):
    return math.degrees(value) if mode == "deg" else math.degrees(value) * (10 / 9) if mode == "grad" else value

def from_angle(value, mode):
    return math.radians(value) if mode == "deg" else math.radians(value) * 0.9 if mode == "grad" else value

def eval_node(node, ctx):
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Var):
        return ctx.get(node.name)
    if isinstance(node, Unary):
        value = eval_node(node.expr, ctx)
        if node.op == "-":
            return -value
        if node.op == "!":
            return factorial(value)
        if node.op == "%":
            return value / 100.0
    if isinstance(node, Binary):
        left = eval_node(node.left, ctx)
        if node.op in ("+", "-") and isinstance(node.right, Unary) and node.right.op == "%":
            amount = left * eval_node(node.right.expr, ctx) / 100.0
            return left + amount if node.op == "+" else left - amount
        right = eval_node(node.right, ctx)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            if right == 0:
                raise EngineError("division by zero")
            return left / right
        if node.op == "^":
            try:
                result = left ** right
            except OverflowError as exc:
                raise EngineError("power overflow") from exc
            except ValueError as exc:
                raise EngineError(str(exc)) from exc
            if math.isinf(result):
                raise EngineError("power overflow")
            return result
    if isinstance(node, Call):
        return call_function(node, ctx)
    raise EngineError("invalid expression")

def call_function(node, ctx):
    values = [eval_node(arg, ctx) for arg in node.args]
    name = node.name.lower()
    if name in ctx.functions:
        params, body = ctx.functions[name]
        if len(values) != len(params):
            raise EngineError(f"{name} expects {len(params)} argument(s)")
        if ctx.depth >= 64:
            raise EngineError("recursion too deep")
        saved = {param: ctx.vars.get(param) for param in params}
        ctx.depth += 1
        try:
            for param, value in zip(params, values):
                ctx.set_var(param, value)
            return eval_node(body, ctx)
        finally:
            ctx.depth -= 1
            for param in params:
                if saved[param] is None:
                    ctx.vars.pop(param, None)
                else:
                    ctx.vars[param] = saved[param]
    if len(values) == 0:
        raise EngineError(f"{name} expects at least one argument")
    first = values[0]
    if name == "sqrt": return math.sqrt(first) if first >= 0 else _math_error("sqrt of negative number")
    if name == "cbrt": return math.copysign(abs(first) ** (1 / 3), first)
    if name == "sin": return math.sin(from_angle(first, ctx.angle))
    if name == "cos": return math.cos(from_angle(first, ctx.angle))
    if name == "tan": return math.tan(from_angle(first, ctx.angle))
    if name == "asin": return to_angle(math.asin(first), ctx.angle) if -1 <= first <= 1 else _math_error("asin out of [-1, 1]")
    if name == "acos": return to_angle(math.acos(first), ctx.angle) if -1 <= first <= 1 else _math_error("acos out of [-1, 1]")
    if name == "atan": return to_angle(math.atan(first), ctx.angle)
    if name == "asinh": return math.asinh(first)
    if name == "acosh": return math.acosh(first) if first >= 1 else _math_error("acosh of value less than 1")
    if name == "atanh": return math.atanh(first) if -1 < first < 1 else _math_error("atanh out of (-1, 1)")
    if name == "log": return math.log10(first) if first > 0 else _math_error("log of non-positive number")
    if name == "log2": return math.log2(first) if first > 0 else _math_error("log2 of non-positive number")
    if name == "ln": return math.log(first) if first > 0 else _math_error("ln of non-positive number")
    if name == "exp": return math.exp(first)
    if name == "abs": return abs(first)
    if name == "floor": return math.floor(first)
    if name == "ceil": return math.ceil(first)
    if name == "round": return round(first)
    if name == "sign": return math.copysign(1.0, first) if first != 0 else 0.0
    if name == "isprime": return is_prime(first)
    if name == "nextprime": return next_prime(first)
    if name == "prevprime": return prev_prime(first)
    if name == "min": return min(values)
    if name == "max": return max(values)
    if name == "clamp":
        if len(values) != 3:
            raise EngineError("clamp expects 3 arguments")
        return min(max(first, values[1]), values[2])
    if name == "gcd": return math.gcd(int(abs(first)), int(abs(values[1]))) if len(values) >= 2 else _math_error("gcd expects 2 arguments")
    if name == "lcm":
        if len(values) < 2:
            raise EngineError("lcm expects 2 arguments")
        a, b = int(abs(first)), int(abs(values[1]))
        return float(abs(a * b) // math.gcd(a, b)) if a and b else 0.0
    if name == "pow":
        if len(values) < 2:
            raise EngineError("pow expects 2 arguments")
        try:
            result = first ** values[1]
        except OverflowError as exc:
            raise EngineError("power overflow") from exc
        if math.isinf(result):
            raise EngineError("power overflow")
        return result
    if name == "mod":
        if len(values) < 2 or values[1] == 0:
            raise EngineError("mod expects a non-zero divisor")
        return first - values[1] * math.floor(first / values[1])
    if name == "hypot":
        if len(values) < 2:
            raise EngineError("hypot expects 2 arguments")
        return math.hypot(first, values[1])
    if name == "ncr":
        if len(values) < 2:
            raise EngineError("ncr expects 2 arguments")
        n, r = int(first), int(values[1])
        return float(math.comb(n, r)) if 0 <= r <= n else 0.0
    if name == "npr":
        if len(values) < 2:
            raise EngineError("npr expects 2 arguments")
        n, r = int(first), int(values[1])
        return float(math.factorial(n) // math.factorial(n - r)) if 0 <= r <= n else 0.0
    if name == "fact": return factorial(first)
    if name in ctx.vars:
        result = ctx.get(name)
        for value in values:
            result *= value
        return result
    raise EngineError(f"unknown function {name!r}")

def _math_error(message):
    raise EngineError(message)

def split_statements(text):
    parts = []
    chunks = re.split(r";|\n", text)
    for chunk in chunks:
        value = chunk.strip()
        if value:
            parts.append(value)
    return parts

FUNCTION_DEF = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)\s*=\s*(.+)$")
VARIABLE_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")

def parse_expression(text):
    return Parser(tokenize(text)).parse()

def eval_statements(text, ctx):
    results = []
    for statement in split_statements(text):
        function = FUNCTION_DEF.match(statement)
        if function:
            name, raw_params, body = function.groups()
            params = [part.strip() for part in raw_params.split(",") if part.strip()]
            for param in params:
                if not NAME.fullmatch(param):
                    raise EngineError(f"invalid parameter {param!r}")
            if len(set(params)) != len(params):
                raise EngineError(f"duplicate parameter in {name}")
            ctx.set_function(name.lower(), tuple(params), parse_expression(body))
            results.append(None)
            continue
        assignment = VARIABLE_ASSIGN.match(statement)
        if assignment and not statement.startswith("("):
            name, expr = assignment.groups()
            value = eval_node(parse_expression(expr), ctx)
            ctx.set_var(name, value)
            results.append(value)
            ctx.vars["ans"] = value
            continue
        value = eval_node(parse_expression(statement), ctx)
        ctx.vars["ans"] = value
        results.append(value)
    return results

def format_number(value):
    if value != value:
        return "nan"
    if value == math.inf:
        return "inf"
    if value == -math.inf:
        return "-inf"
    if value == 0:
        return "0"
    if value == math.floor(value) and abs(value) < 9.2e18:
        return str(int(value))
    text = format(value, ".12g")
    if "e" not in text and "E" not in text:
        return text.rstrip("0").rstrip(".") if "." in text else text
    return text.replace("e+0", "e").replace("e-0", "e-")
