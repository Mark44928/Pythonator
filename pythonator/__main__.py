import argparse
import json
import math
import os
import pathlib
import statistics
import sys
import tempfile

from . import __version__
from .engine import Context, EngineError, eval_statements, eval_node, parse_expression, format_number
from .theme import THEMES, color, theme_names


def config_path():
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = pathlib.Path(xdg).expanduser() if xdg else pathlib.Path.home() / ".config"
    return base / "pythonator" / "config.json"


def history_path():
    xdg = os.environ.get("XDG_STATE_HOME")
    base = pathlib.Path(xdg).expanduser() if xdg else pathlib.Path.home() / ".local" / "state"
    return base / "pythonator" / "history"


def load_config():
    path = config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {"theme": "greenit", "angle": "rad"}


def save_config(config):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(config, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="pythonator_config_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_history():
    try:
        lines = history_path().read_text(encoding="utf-8", errors="ignore").splitlines()
        cleaned = []
        for line in lines:
            line = "".join(ch for ch in line if ch.isprintable())
            if line:
                cleaned.append(line)
        return cleaned[-200:]
    except OSError:
        return []


def save_history(history):
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="pythonator_history_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for line in history[-200:]:
                handle.write(line + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def last_result(results):
    for value in reversed(results):
        if value is not None:
            return value
    return None


def eval_cli(expression, angle="rad"):
    context = Context()
    context.angle = angle
    results = eval_statements(expression, context)
    return last_result(results)


def parse_numbers(arguments):
    cleaned = arguments.replace(",", " ").replace(";", " ").split()
    values = []
    for token in cleaned:
        try:
            value = float(token)
        except ValueError as exc:
            raise EngineError(f"invalid number {token!r}") from exc
        if not math.isfinite(value):
            raise EngineError(f"{token!r} is not finite")
        values.append(value)
    return values


def prime_factors(n):
    n = int(abs(n))
    factors = []
    divisor = 2
    while divisor * divisor <= n:
        while n % divisor == 0:
            factors.append(divisor)
            n //= divisor
        divisor += 1 if divisor == 2 else 2
    if n > 1:
        factors.append(n)
    return factors


def plot_expression(expr, minimum, maximum):
    width = 57
    height = 17
    values = []
    for column in range(width):
        x = minimum + (maximum - minimum) * column / (width - 1)
        context = Context()
        context.vars["x"] = x
        try:
            value = eval_node(parse_expression(expr), context)
            values.append(value if math.isfinite(value) else None)
        except EngineError:
            values.append(None)
    finite = [value for value in values if value is not None]
    if not finite:
        raise EngineError(f"no real values in [{minimum}, {maximum}]")
    y_min, y_max = min(finite), max(finite)
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    pad = (y_max - y_min) * 0.08
    y_min -= pad
    y_max += pad
    grid = [[" "] * width for _ in range(height)]
    for column, value in enumerate(values):
        if value is None:
            continue
        row = round((y_max - value) / (y_max - y_min) * (height - 1))
        row = max(0, min(height - 1, row))
        grid[row][column] = "█"
    for row in grid:
        print("".join(row).rstrip())
    print(f"x {format_number(minimum)} … {format_number(maximum)}   y {format_number(y_min)} … {format_number(y_max)}")


def help_text(version):
    return f"""Pythonator {version} — a dependency-free Python calculator REPL
Usage:
  pythonator
  pythonator --eval "2+3*4"
  pythonator --eval "sqrt(16)" --json

Commands:
  help                  show this help
  vars                  list variables
  funcs                 list user functions
  reset                 clear user variables and functions
  del <name>            delete a variable or function
  theme [name]          list themes or set the active theme
  angle rad|deg|grad    set the angle unit
  stats <n...>          count/min/max/sum/mean/median/stddev
  primes [n]            list primes up to n
  factorize <n>         prime factorization of n
  table <expr> [a b]     evaluate f(x) across a range
  plot <expr> [a b]      ASCII plot across a range
  exit, quit, q          leave Pythonator
"""


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--eval", dest="expression")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--version", "-V", action="store_true")
    args, remaining = parser.parse_known_args(argv)
    if args.help:
        print(help_text(__version__), end="")
        return 0
    if args.version:
        print(f"pythonator {__version__}")
        return 0
    if args.expression is not None:
        try:
            result = eval_cli(args.expression)
            if args.json:
                print(json.dumps({"expression": args.expression, "result": result}, separators=(",", ":")))
            elif result is not None:
                print(format_number(result))
            return 0
        except EngineError as exc:
            if args.json:
                print(json.dumps({"expression": args.expression, "error": str(exc)}, separators=(",", ":")))
                return 0
            print(args.expression, file=sys.stderr)
            print("^", file=sys.stderr)
            print(str(exc), file=sys.stderr)
            return 0
    if args.json:
        print("--json requires --eval <expr>", file=sys.stderr)
        return 2
    return run_repl()


def run_repl(context=None, input_func=input, output=print):
    config = load_config()
    theme = THEMES.get(config.get("theme"), THEMES["greenit"])
    history = load_history()
    context = context or Context()
    context.angle = config.get("angle", "rad")
    rule = color(theme[2], "─" * 57) if sys.stdout.isatty() else "─" * 57
    banner = color(theme[0], "⟨ py ⟩", bold=True) + " Pythonator" if sys.stdout.isatty() else "Pythonator"
    output(banner)
    output(rule)
    output(color(theme[3], "type help for commands; 2+3*4 works") if sys.stdout.isatty() else "type help for commands; 2+3*4 works")

    def save_state():
        config["theme"] = config.get("theme", "greenit")
        config["angle"] = context.angle
        save_config(config)
        save_history(history)

    while True:
        try:
            line = input_func(color(theme[0], "⟨ py ⟩ ") if sys.stdout.isatty() else "py> ")
        except (EOFError, KeyboardInterrupt):
            output("")
            save_state()
            return 0
        stripped = line.strip()
        if not stripped:
            continue
        if not history or stripped != history[-1]:
            history.append(stripped)
        command, _, rest = stripped.partition(" ")
        command = command.lower()
        rest = rest.strip()
        if command in ("exit", "quit", "q"):
            save_state()
            return 0
        if command == "help":
            output(help_text(__version__), end="")
            continue
        if command == "clear":
            output("\033[2J\033[H", end="")
            continue
        if command == "vars":
            for name, value in sorted(context.vars.items()):
                if name not in ("ans",) and not name.startswith("m_"):
                    output(f"{name:<10} {format_number(value)}")
            continue
        if command == "funcs":
            for name, (params, _) in sorted(context.functions.items()):
                output(f"{name}({', '.join(params)})")
            continue
        if command == "reset":
            context.reset()
            output("reset")
            continue
        if command == "del":
            if not rest:
                output("del <name>")
            else:
                context.vars.pop(rest, None)
                context.functions.pop(rest, None)
                output(f"deleted {rest}")
            continue
        if command == "theme":
            if not rest:
                output("themes: " + ", ".join(theme_names()))
            elif rest in THEMES:
                config["theme"] = rest
                theme = THEMES[rest]
                save_state()
                output(f"theme {rest}")
            else:
                output(f"unknown theme: {rest}")
            continue
        if command == "angle":
            if rest in ("rad", "deg", "grad"):
                context.angle = rest
                save_state()
                output(f"angle {rest}")
            else:
                output(f"angle is {context.angle}")
            continue
        if command == "stats":
            try:
                values = parse_numbers(rest)
                if not values:
                    raise EngineError("stats needs numbers")
                output(f"count  {len(values)}")
                output(f"min    {format_number(min(values))}")
                output(f"max    {format_number(max(values))}")
                output(f"sum    {format_number(sum(values))}")
                output(f"mean   {format_number(statistics.fmean(values))}")
                output(f"median {format_number(statistics.median(values))}")
                output(f"stddev {format_number(statistics.pstdev(values))}")
            except EngineError as exc:
                output(str(exc))
            continue
        if command == "primes":
            try:
                n = int(float(rest or "100"))
                if n < 2:
                    output("primes needs n >= 2")
                    continue
                n = min(n, 1000)
                primes = [value for value in range(2, n + 1) if all(value % d for d in range(2, int(math.sqrt(value)) + 1))]
                output(" ".join(str(value) for value in primes))
            except ValueError:
                output("primes [n]")
            continue
        if command == "factorize":
            try:
                n = int(float(rest))
                if n == 0:
                    output("factorize expects n != 0")
                    continue
                factors = prime_factors(n)
                output(f"{n} = " + " × ".join(str(factor) for factor in factors))
            except ValueError:
                output("factorize <n>")
            continue
        if command == "table":
            try:
                expression, _, span = rest.partition(" ")
                bounds = [float(part) for part in span.split()] if span else [-10.0, 10.0]
                if len(bounds) == 1:
                    bounds = [-10.0, bounds[0]]
                if len(bounds) != 2:
                    raise EngineError("table takes an expression and optional xmin xmax")
                minimum, maximum = bounds
                for index in range(16):
                    x = minimum + (maximum - minimum) * index / 15
                    context.vars["x"] = x
                    value = eval_node(parse_expression(expression), context)
                    output(f"{format_number(x):>12} {format_number(value):>18}")
            except EngineError as exc:
                output(str(exc))
            continue
        if command == "plot":
            try:
                expression, _, span = rest.partition(" ")
                bounds = [float(part) for part in span.split()] if span else [-10.0, 10.0]
                if len(bounds) == 1:
                    bounds = [-10.0, bounds[0]]
                if len(bounds) != 2:
                    raise EngineError("plot takes an expression and optional xmin xmax")
                plot_expression(expression, bounds[0], bounds[1])
            except EngineError as exc:
                output(str(exc))
            continue
        try:
            results = eval_statements(line, context)
            value = last_result(results)
            if value is not None:
                output("= " + format_number(value))
        except EngineError as exc:
            output(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
