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
from .lineedit import LineEditor
from .theme import ALL_THEMES, color, get_theme, theme_names

BANNER = r"""
 ____        _   _                       _
|  _ \ _   _| |_| |__   ___  _ __   __ _| |_ ___  _ __
| |_) | | | | __| '_ \ / _ \| '_ \ / _` | __/ _ \| '__|
|  __/| |_| | |_| | | | (_) | | | | (_| | || (_) | |
|_|    \__, |\__|_| |_|\___/|_| |_|\__,_|\__\___/|_|
       |___/
"""

def color_enabled():
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"

def paint(value, text, bold=False, dim=False, italic=False):
    if not color_enabled():
        return text
    return color(value, text, bold=bold, dim=dim, italic=italic)

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

def last_result(results):
    for value in reversed(results):
        if value is not None:
            return value
    return None

def eval_cli(expression, angle="rad"):
    context = Context()
    context.angle = angle
    return last_result(eval_statements(expression, context))

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
  version               show version
  exit, quit, q          leave Pythonator
"""

def banner_rows():
    rows = [row.rstrip() for row in BANNER.strip("\n").splitlines()]
    return [row for row in rows if row]

def print_banner(theme):
    rows = banner_rows()
    count = len(rows)
    for index, row in enumerate(rows):
        f = index / (count - 1) if count > 1 else 0.0
        if f < 0.33:
            t = f * 3.0
            base, target = theme.accent, theme.prompt
        elif f < 0.66:
            t = (f - 0.33) * 3.0
            base, target = theme.prompt, theme.result
        else:
            t = min(1.0, max(0.0, (f - 0.66) * 3.0))
            base, target = theme.result, theme.accent
        mixed = tuple(round(base[i] * (1 - t) + target[i] * t) for i in range(3))
        print(paint(mixed, row, bold=True))

def rule_line(theme, context):
    status = f"{theme.name} · {len(context.vars)} vars {len(context.functions)} funcs"
    if context.angle != "rad":
        status += f" · {context.angle}"
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80
    cells = max(0, width - len(status) - 2)
    parts = []
    for index in range(cells):
        f = 1.0 - abs(2.0 * index / (cells - 1) - 1.0) if cells > 1 else 1.0
        mixed = tuple(round(theme.hint[i] * (1 - f) + theme.accent[i] * f) for i in range(3))
        parts.append(paint(mixed, "─"))
    print("".join(parts) + "  " + paint(theme.hint, status, dim=True))

def prompt_text(theme, error_flash):
    bracket = paint(theme.accent, "⟨", bold=True)
    name = paint(theme.hint, "py", italic=True)
    close = paint(theme.accent, "⟩")
    accent = (255, 100, 140) if error_flash else theme.accent
    arrow = paint(accent, "➤", bold=True)
    return f"{bracket} {name} {close} {arrow} "

def transient_prompt(theme):
    return (
        paint(theme.hint, "⟨", dim=True)
        + " "
        + paint(theme.hint, "··", dim=True)
        + " "
        + paint(theme.hint, "⟩", dim=True)
        + " "
        + paint(theme.hint, "➤", bold=True, dim=True)
        + " "
    )

def print_transient(theme, line):
    text = paint(theme.hint, "⟨ ·· ⟩ ➤ " + line, dim=True)
    sys.stdout.write("\r\033[K" + text + "\n")
    sys.stdout.flush()

def print_error(theme, line, error, column=1):
    print(paint(theme.prompt, line))
    print(" " * max(0, column - 1) + paint(theme.error, "^"))
    print(paint(theme.error, str(error)))

def run_repl():
    config = load_config()
    theme = get_theme(config.get("theme", "greenit"))
    context = Context()
    context.angle = config.get("angle", "rad")
    editor = LineEditor(history_path())
    error_flash = False
    print_banner(theme)
    print(
        paint(theme.hint, "Tip: type ")
        + paint(theme.prompt, "help", bold=True)
        + paint(theme.hint, " for commands, or enter an expression to calculate.")
    )
    while True:
        rule_line(theme, context)
        editor.transient_prompt = transient_prompt(theme)
        line = editor.edit(prompt_text(theme, error_flash))
        error_flash = False
        if line is None:
            break
        if not isinstance(line, str) or not line.strip():
            continue
        print_transient(theme, line)
        stripped = line.strip()
        command, _, rest = stripped.partition(" ")
        command = command.lower()
        rest = rest.strip()
        if command in ("exit", "quit", "q"):
            break
        if command == "help":
            print(help_text(__version__), end="")
            continue
        if command == "version" or command == "about":
            print(paint(theme.prompt, f"pythonator {__version__}", bold=True))
            continue
        if command == "clear":
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
            print_banner(theme)
            print(
                paint(theme.hint, "Tip: type ")
                + paint(theme.prompt, "help", bold=True)
                + paint(theme.hint, " for commands, or enter an expression to calculate.")
            )
            continue
        if command == "vars":
            for name, value in sorted(context.vars.items()):
                if name != "ans":
                    print(paint(theme.hint, f"{name:<10}") + paint(theme.result, format_number(value)))
            continue
        if command == "funcs":
            for name, (params, _) in sorted(context.functions.items()):
                print(paint(theme.prompt, f"{name}({', '.join(params)})"))
            continue
        if command == "reset":
            context.reset()
            print(paint(theme.prompt, "reset"))
            continue
        if command == "del":
            if not rest:
                print(paint(theme.error, "del <name>"))
            else:
                context.vars.pop(rest, None)
                context.functions.pop(rest, None)
                print(paint(theme.hint, f"deleted {rest}"))
            continue
        if command == "theme":
            if not rest:
                for name in theme_names():
                    swatch = get_theme(name)
                    print(paint(swatch.accent, "●", bold=True) + " " + name)
            elif rest in theme_names():
                theme = get_theme(rest)
                config["theme"] = rest
                save_config(config)
                print(paint(theme.prompt, f"theme {rest}"))
            else:
                print(paint(theme.error, f"unknown theme: {rest}"))
            continue
        if command == "angle":
            if rest in ("rad", "deg", "grad"):
                context.angle = rest
                config["angle"] = rest
                save_config(config)
                print(paint(theme.prompt, f"angle {rest}"))
            else:
                print(paint(theme.hint, f"angle is {context.angle}"))
            continue
        if command == "stats":
            try:
                values = parse_numbers(rest)
                if not values:
                    raise EngineError("stats needs numbers")
                for label, value in (
                    ("count", len(values)),
                    ("min", min(values)),
                    ("max", max(values)),
                    ("sum", sum(values)),
                    ("mean", statistics.fmean(values)),
                    ("median", statistics.median(values)),
                    ("stddev", statistics.pstdev(values)),
                ):
                    text = str(value) if label == "count" else format_number(value)
                    print(paint(theme.hint, f"{label:<6}") + paint(theme.result, text))
            except EngineError as exc:
                print(paint(theme.error, str(exc)))
            continue
        if command == "primes":
            try:
                n = int(float(rest or "100"))
                if n < 2:
                    print(paint(theme.error, "primes needs n >= 2"))
                    continue
                n = min(n, 1000)
                primes = [value for value in range(2, n + 1) if all(value % d for d in range(2, int(math.sqrt(value)) + 1))]
                print(paint(theme.result, " ".join(str(value) for value in primes)))
            except ValueError:
                print(paint(theme.error, "primes [n]"))
            continue
        if command == "factorize":
            try:
                n = int(float(rest))
                if n == 0:
                    print(paint(theme.error, "factorize expects n != 0"))
                    continue
                factors = prime_factors(n)
                print(paint(theme.result, f"{n} = " + " × ".join(str(factor) for factor in factors)))
            except ValueError:
                print(paint(theme.error, "factorize <n>"))
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
                    print(paint(theme.hint, f"{format_number(x):>12}") + " " + paint(theme.result, f"{format_number(value):>18}"))
            except EngineError as exc:
                print(paint(theme.error, str(exc)))
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
                print(paint(theme.error, str(exc)))
            continue
        try:
            results = eval_statements(line, context)
            value = last_result(results)
            if value is not None:
                print(paint(theme.result, "= " + format_number(value)))
        except EngineError as exc:
            error_flash = True
            print_error(theme, line, exc)
    save_config(config)
    print()

def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--eval", dest="expression")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--version", "-V", action="store_true")
    args, _ = parser.parse_known_args(argv)
    if args.help:
        print(help_text(__version__), end="")
        return 0
    if args.version:
        print(f"pythonator {__version__}")
        return 0
    if args.expression is not None:
        config = load_config()
        theme = get_theme(config.get("theme", "greenit"))
        try:
            result = eval_cli(args.expression, config.get("angle", "rad"))
            if args.json:
                print(json.dumps({"expression": args.expression, "result": result}, separators=(",", ":")))
            elif result is not None:
                text = format_number(result)
                print(paint(theme.result, text) if color_enabled() else text)
            return 0
        except EngineError as exc:
            if args.json:
                print(json.dumps({"expression": args.expression, "error": str(exc)}, separators=(",", ":")))
                return 0
            print(args.expression)
            print("^")
            print(str(exc))
            return 0
    if args.json:
        print("--json requires --eval <expr>", file=sys.stderr)
        return 2
    return run_repl()

if __name__ == "__main__":
    raise SystemExit(main())
