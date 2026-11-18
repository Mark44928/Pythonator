import math
import cmath
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
    "i": 1j,
}
BUILTIN_FUNCTIONS = {
    "sqrt", "cbrt", "sin", "cos", "tan", "asin", "acos", "atan",
    "asinh", "acosh", "atanh", "log", "log2", "ln", "exp", "abs",
    "floor", "ceil", "round", "sign", "isprime", "nextprime", "prevprime",
    "min", "max", "clamp", "gcd", "lcm", "pow", "mod", "hypot",
    "ncr", "npr", "fact", "arg", "re", "im", "conj",
    "normpdf", "normcdf", "binompdf", "binomcdf", "poissonpdf", "poissoncdf",
    "logistic", "erf", "det2", "det3", "divcount", "totient",
    "modpow", "floordiv", "ceildiv",
}
RESERVED = set(CONSTANTS) | BUILTIN_FUNCTIONS | {"ans"}

def is_finite(value):
    if isinstance(value, complex):
        return math.isfinite(value.real) and math.isfinite(value.imag)
    return math.isfinite(value)

def is_real(value):
    return not isinstance(value, complex) or value.imag == 0

def finite_real(value, label="argument"):
    if not is_real(value) or not is_finite(value):
        raise EngineError(f"{label} must be a finite real number")
    return value.real if isinstance(value, complex) else value

def is_prime(number):
    if isinstance(number, complex) or not math.isfinite(number) or number > 1e12:
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
    if isinstance(number, complex) or not math.isfinite(number) or number > 1e12:
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
    if isinstance(number, complex) or not math.isfinite(number) or number > 1e12:
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
        self.radix = 10
        self.memory = 0.0
        self.has_memory = False
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
    if isinstance(value, complex) or not math.isfinite(value) or value < 0 or value != math.floor(value) or value > 170:
        raise EngineError("factorial argument must be a non-negative integer <= 170")
    n = int(math.floor(value))
    result = 1
    for item in range(2, n + 1):
        result *= item
    return float(result)

def _whole(value, label, maximum=10**12):
    number = finite_real(value, label)
    if number < 0 or number > maximum or number != math.floor(number):
        raise EngineError(f"{label} must be a non-negative integer <= {maximum}")
    return int(number)

def _divcount(number):
    n = _whole(number, "divcount argument")
    if n == 0:
        return float("inf")
    count = 0
    d = 1
    while d <= n // d:
        if n % d == 0:
            count += 2 if d * d != n else 1
        d += 1
    return float(count)

def _totient(number):
    n = _whole(number, "totient argument", 10**9)
    if n <= 1:
        return 1.0 if n == 1 else 0.0
    result = n
    factor = 2
    rest = n
    while factor * factor <= rest:
        if rest % factor == 0:
            result -= result // factor
            while rest % factor == 0:
                rest //= factor
        factor += 1 if factor == 2 else 2
    if rest > 1:
        result -= result // rest
    return float(result)

def _modpow(base, exponent, modulus):
    base_i = int(finite_real(base, "modpow base"))
    if abs(base_i) > 10**15:
        raise EngineError("modpow base is out of range")
    exp_i = _whole(exponent, "modpow exponent", 10**12)
    mod_i = _whole(modulus, "modpow modulus", 10**15)
    if mod_i == 0:
        raise EngineError("modpow modulus cannot be zero")
    return float(pow(base_i, exp_i, mod_i))

def _log_comb(n, r):
    try:
        return math.lgamma(n + 1) - math.lgamma(r + 1) - math.lgamma(n - r + 1)
    except (OverflowError, ValueError):
        return math.inf

def _log_perm(n, r):
    try:
        return math.lgamma(n + 1) - math.lgamma(n - r + 1)
    except (OverflowError, ValueError):
        return math.inf

def _log_result_fits(log_value):
    return math.isfinite(log_value) and log_value <= math.log(1.7976931348623157e308)

def to_angle(value, mode):
    return math.degrees(value) if mode == "deg" else math.degrees(value) * (10 / 9) if mode == "grad" else value

def from_angle(value, mode):
    return math.radians(value) if mode == "deg" else math.radians(value) * 0.9 if mode == "grad" else value

def format_ast(node):
    lines = []

    def walk(item, prefix="", is_last=True):
        branch = "└─ " if is_last else "├─ "
        if isinstance(item, Num):
            lines.append(f"{prefix}{branch}Num {format_number(item.value)}")
            return
        if isinstance(item, Var):
            lines.append(f"{prefix}{branch}Var {item.name}")
            return
        if isinstance(item, Unary):
            label = {"-": "Negate", "!": "Factorial", "%": "Percent"}.get(item.op, item.op)
            lines.append(f"{prefix}{branch}{label}")
            child_prefix = prefix + ("   " if is_last else "│  ")
            walk(item.expr, child_prefix, True)
            return
        if isinstance(item, Binary):
            lines.append(f"{prefix}{branch}Binary {item.op}")
            child_prefix = prefix + ("   " if is_last else "│  ")
            walk(item.left, child_prefix, False)
            walk(item.right, child_prefix, True)
            return
        if isinstance(item, Call):
            lines.append(f"{prefix}{branch}Call {item.name}(")
            child_prefix = prefix + ("   " if is_last else "│  ")
            for index, arg in enumerate(item.args):
                walk(arg, child_prefix, index == len(item.args) - 1)
            return
        lines.append(f"{prefix}{branch}Unknown")

    lines.append("Expression")
    walk(node, "", True)
    return "\n".join(lines)

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
            except ZeroDivisionError as exc:
                raise EngineError("division by zero") from exc
            if not is_finite(result):
                raise EngineError("power overflow")
            return result
    if isinstance(node, Call):
        return call_function(node, ctx)
    raise EngineError("invalid expression")

def call_function(node, ctx):
    try:
        return _call_function(node, ctx)
    except EngineError:
        raise
    except (ValueError, OverflowError) as exc:
        raise EngineError(str(exc)) from exc

def _call_function(node, ctx):
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
                # Bind params directly (not set_var) so names like "pi" can
                # shadow built-ins inside the function body, matching the
                # C++ engine's local-frame semantics.
                ctx.vars[param] = value
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
    if is_real(first) and isinstance(first, complex):
        # Arithmetic can produce complex values with a zero imaginary part;
        # built-ins that use math.* must receive a plain float.
        first = first.real
    if name == "sqrt": return cmath.sqrt(first)
    if name == "cbrt":
        if not is_real(first):
            return cmath.exp(cmath.log(first) / 3)
        return math.copysign(abs(first) ** (1 / 3), first)
    if name == "sin": return cmath.sin(first) if not is_real(first) else math.sin(from_angle(first, ctx.angle))
    if name == "cos": return cmath.cos(first) if not is_real(first) else math.cos(from_angle(first, ctx.angle))
    if name == "tan": return cmath.tan(first) if not is_real(first) else math.tan(from_angle(first, ctx.angle))
    if name == "asin":
        if not is_real(first): return cmath.asin(first)
        return to_angle(math.asin(first), ctx.angle) if -1 <= first <= 1 else _math_error("asin out of [-1, 1]")
    if name == "acos":
        if not is_real(first): return cmath.acos(first)
        return to_angle(math.acos(first), ctx.angle) if -1 <= first <= 1 else _math_error("acos out of [-1, 1]")
    if name == "atan": return cmath.atan(first) if not is_real(first) else to_angle(math.atan(first), ctx.angle)
    if name == "asinh": return cmath.asinh(first) if not is_real(first) else math.asinh(first)
    if name == "acosh":
        if not is_real(first): return cmath.acosh(first)
        return math.acosh(first) if first >= 1 else _math_error("acosh of value less than 1")
    if name == "atanh":
        if not is_real(first): return cmath.atanh(first)
        return math.atanh(first) if -1 < first < 1 else _math_error("atanh out of (-1, 1)")
    if name == "log":
        if not is_real(first): return cmath.log10(first)
        return math.log10(first) if first > 0 else _math_error("log of non-positive number")
    if name == "log2":
        if not is_real(first): return cmath.log(first, 2)
        return math.log2(first) if first > 0 else _math_error("log2 of non-positive number")
    if name == "ln":
        if not is_real(first): return cmath.log(first)
        return math.log(first) if first > 0 else _math_error("ln of non-positive number")
    if name == "exp":
        try:
            return cmath.exp(first) if not is_real(first) else math.exp(first)
        except OverflowError as exc:
            raise EngineError("exp overflow") from exc
    if name == "abs": return abs(first)
    if name in ("floor", "ceil", "round"):
        value = finite_real(first, name)
        return math.floor(value) if name == "floor" else math.ceil(value) if name == "ceil" else round(value)
    if name == "sign":
        if not is_real(first):
            return first / abs(first) if first != 0 else 0j
        return math.copysign(1.0, first) if first != 0 else 0.0
    if name == "arg": return cmath.phase(first)
    if name == "re": return first.real if isinstance(first, complex) else first
    if name == "im": return first.imag if isinstance(first, complex) else 0.0
    if name == "conj": return first.conjugate() if isinstance(first, complex) else first
    if name == "isprime":
        return is_prime(finite_real(first, "isprime argument"))
    if name == "nextprime":
        return next_prime(finite_real(first, "nextprime argument"))
    if name == "prevprime":
        return prev_prime(finite_real(first, "prevprime argument"))
    if name == "min":
        return min(finite_real(value, "min argument") for value in values)
    if name == "max":
        return max(finite_real(value, "max argument") for value in values)
    if name == "clamp":
        if len(values) != 3:
            raise EngineError("clamp expects 3 arguments")
        low, high = finite_real(values[1], "clamp argument"), finite_real(values[2], "clamp argument")
        return min(max(finite_real(first, "clamp argument"), low), high)
    if name == "gcd":
        if len(values) < 2:
            raise EngineError("gcd expects 2 arguments")
        a = finite_real(first, "gcd argument")
        b = finite_real(values[1], "gcd argument")
        return float(math.gcd(int(abs(a)), int(abs(b))))
    if name == "lcm":
        if len(values) < 2:
            raise EngineError("lcm expects 2 arguments")
        a = finite_real(first, "lcm argument")
        b = finite_real(values[1], "lcm argument")
        a, b = int(abs(a)), int(abs(b))
        if not (a and b):
            return 0.0
        multiple = (a // math.gcd(a, b)) * b
        try:
            return float(multiple)
        except OverflowError as exc:
            raise EngineError("lcm result too large") from exc
    if name == "pow":
        if len(values) < 2:
            raise EngineError("pow expects 2 arguments")
        try:
            result = first ** values[1]
        except OverflowError as exc:
            raise EngineError("power overflow") from exc
        except ZeroDivisionError as exc:
            raise EngineError("division by zero") from exc
        if not is_finite(result):
            raise EngineError("power overflow")
        return result
    if name == "mod":
        a = finite_real(first, "mod argument")
        b = finite_real(values[1], "mod argument") if len(values) > 1 else 0
        if len(values) < 2 or b == 0:
            raise EngineError("mod expects a non-zero divisor")
        return a - b * math.floor(a / b)
    if name == "hypot":
        if len(values) < 2:
            raise EngineError("hypot expects 2 arguments")
        return math.hypot(finite_real(first, "hypot argument"), finite_real(values[1], "hypot argument"))
    if name == "ncr":
        if len(values) < 2:
            raise EngineError("ncr expects 2 arguments")
        first = finite_real(first, "ncr argument")
        second = finite_real(values[1], "ncr argument")
        n, r = int(first), int(second)
        if not (0 <= r <= n):
            return 0.0
        if r == 0 or r == n:
            return 1.0
        if r == 1 or r == n - 1:
            return float(n)
        # Reject before math.comb allocates a big integer: the float result is
        # all this API can return, so anything past its range is unusable.
        if not _log_result_fits(_log_comb(n, r)):
            raise EngineError("ncr result too large")
        try:
            return float(math.comb(n, r))
        except OverflowError as exc:
            raise EngineError("ncr result too large") from exc
    if name == "npr":
        if len(values) < 2:
            raise EngineError("npr expects 2 arguments")
        first = finite_real(first, "npr argument")
        second = finite_real(values[1], "npr argument")
        n, r = int(first), int(second)
        if not (0 <= r <= n):
            return 0.0
        if r == 0:
            return 1.0
        if r == 1:
            return float(n)
        if not _log_result_fits(_log_perm(n, r)):
            raise EngineError("npr result too large")
        try:
            return float(math.perm(n, r))
        except OverflowError as exc:
            raise EngineError("npr result too large") from exc
    if name == "fact": return factorial(first)
    if name == "normpdf":
        if len(values) != 3:
            raise EngineError("normpdf expects x, mean and stddev")
        x, mu, sd = (finite_real(value, "normpdf argument") for value in values)
        if sd <= 0:
            raise EngineError("normpdf stddev must be positive")
        z = (x - mu) / sd
        return math.exp(-0.5 * z * z) / (sd * math.sqrt(2 * math.pi))
    if name == "normcdf":
        if len(values) != 3:
            raise EngineError("normcdf expects x, mean and stddev")
        x, mu, sd = (finite_real(value, "normcdf argument") for value in values)
        if sd <= 0:
            raise EngineError("normcdf stddev must be positive")
        return 0.5 * (1 + math.erf((x - mu) / (sd * math.sqrt(2))))
    if name == "binompdf":
        if len(values) != 3:
            raise EngineError("binompdf expects k, n and p")
        k = _whole(values[0], "binompdf k", 10**6)
        n = _whole(values[1], "binompdf n", 10**6)
        p = finite_real(values[2], "binompdf p")
        if p < 0 or p > 1 or k > n:
            raise EngineError("binompdf requires 0 <= p <= 1 and 0 <= k <= n")
        if p == 0:
            return 1.0 if k == 0 else 0.0
        if p == 1:
            return 1.0 if k == n else 0.0
        log_term = (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                    + k * math.log(p) + (n - k) * math.log1p(-p))
        return math.exp(log_term) if log_term > -745 else 0.0
    if name == "binomcdf":
        if len(values) != 3:
            raise EngineError("binomcdf expects k, n and p")
        k = _whole(values[0], "binomcdf k", 10**6)
        n = _whole(values[1], "binomcdf n", 10**6)
        p = finite_real(values[2], "binomcdf p")
        if p < 0 or p > 1 or k > n:
            raise EngineError("binomcdf requires 0 <= p <= 1 and 0 <= k <= n")
        if p == 0:
            return 1.0
        if p == 1:
            return 1.0 if k == n else 0.0
        term = math.exp(n * math.log1p(-p))
        total = term
        ratio = p / (1 - p)
        for index in range(1, k + 1):
            term *= (n - index + 1) / index * ratio
            total += term
        return min(1.0, max(0.0, total))
    if name == "poissonpdf":
        if len(values) != 2:
            raise EngineError("poissonpdf expects k and lambda")
        k = _whole(values[0], "poissonpdf k", 10**6)
        lam = finite_real(values[1], "poissonpdf lambda")
        if lam <= 0:
            raise EngineError("poissonpdf lambda must be positive")
        log_term = k * math.log(lam) - lam - math.lgamma(k + 1)
        return math.exp(log_term) if log_term > -745 else 0.0
    if name == "poissoncdf":
        if len(values) != 2:
            raise EngineError("poissoncdf expects k and lambda")
        k = _whole(values[0], "poissoncdf k", 10**6)
        lam = finite_real(values[1], "poissoncdf lambda")
        if lam <= 0:
            raise EngineError("poissoncdf lambda must be positive")
        term = math.exp(-lam)
        total = term
        for index in range(1, k + 1):
            term *= lam / index
            total += term
        return min(1.0, max(0.0, total))
    if name == "logistic":
        return 1 / (1 + math.exp(-finite_real(first, "logistic argument")))
    if name == "erf":
        return math.erf(finite_real(first, "erf argument"))
    if name == "det2":
        if len(values) != 4:
            raise EngineError("det2 expects a, b, c, d")
        a, b, c, d = (finite_real(value, "det2 argument") for value in values)
        return a * d - b * c
    if name == "det3":
        if len(values) != 9:
            raise EngineError("det3 expects nine entries, rows first")
        m = [finite_real(value, "det3 argument") for value in values]
        return (m[0] * m[4] * m[8] + m[1] * m[5] * m[6] + m[2] * m[3] * m[7] -
                m[2] * m[4] * m[6] - m[1] * m[3] * m[8] - m[0] * m[5] * m[7])
    if name == "divcount":
        return _divcount(first)
    if name == "totient":
        return _totient(first)
    if name == "modpow":
        if len(values) != 3:
            raise EngineError("modpow expects base, exponent and modulus")
        return _modpow(values[0], values[1], values[2])
    if name == "floordiv":
        if len(values) != 2:
            raise EngineError("floordiv expects dividend and divisor")
        a, b = (finite_real(value, "floordiv argument") for value in values)
        if b == 0:
            raise EngineError("floordiv by zero")
        return math.floor(a / b)
    if name == "ceildiv":
        if len(values) != 2:
            raise EngineError("ceildiv expects dividend and divisor")
        a, b = (finite_real(value, "ceildiv argument") for value in values)
        if b == 0:
            raise EngineError("ceildiv by zero")
        return math.ceil(a / b)
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

def format_complex(value):
    if value.imag == 0:
        return format_number(value.real)
    re = format_number(value.real)
    im = format_number(abs(value.imag))
    if im == "1":
        im = ""
    sign = "-" if value.imag < 0 else "+"
    if value.real == 0:
        return ("-" if value.imag < 0 else "") + im + "i"
    return re + sign + im + "i"

def format_number(value):
    if isinstance(value, complex):
        return format_complex(value)
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

def format_value(value, radix=10):
    if isinstance(value, complex):
        if value.imag != 0:
            return format_complex(value)
        value = value.real
    if not math.isfinite(value):
        return format_number(value)
    if radix in (16, 2) and value == math.floor(value) and abs(value) < 9.2e18:
        negative = value < 0
        number = int(abs(value))
        if radix == 16:
            text = format(number, "x")
            return ("-" if negative else "") + "0x" + text
        return ("-" if negative else "") + "0b" + format(number, "b")
    if radix == 0:
        return format(value, ".6e")
    return format_number(value)
