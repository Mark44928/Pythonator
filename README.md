# Pythonator

A **dependency-free Python rewrite of Plusalator**: a calculator REPL and headless `--eval` CLI with Qalculate-style math, written in pure standard-library Python.

## Why

Plusalator is a polished C++17 terminal calculator. Pythonator ports the same idea to Python: implicit multiplication, percent postfix, factorial, hex/bin/oct literals, user functions, built-in constants, angle units, and a REPL that stays out of your way.

No API key. No `eval()`. No dependencies.

## Install

```bash
git clone https://github.com/Mark44928/Pythonator.git
cd Pythonator
./install.sh
pythonator
```

From a clone without installing:

```bash
python -m pythonator
```

## The Plusalator look

Pythonator keeps Plusalator’s visual language:

- a pyfiglet `standard` banner for Pythonator, rendered through an accent → prompt → result gradient
- a full-width gradient rule with the current theme, var/function count, angle unit, radix mode and memory flag
- the `⟨ py ⟩ ➤` prompt, dim `⟨ ·· ⟩ ➤` transient line and colored `= result`
- all 18 Plusalator theme names, with the same RGB tables
- a raw-mode line editor: arrow keys, Home/End, Delete, Ctrl+A/E/U/K/L/F, bracketed paste, prefix history and ghost autosuggest
- `theme <name>`, `angle rad|deg|grad`, `mode dec|hex|bin|sci`, memory slots, `help`, `vars`, `funcs`, `stats`, `primes`, `factorize`, `table` and `plot`

## Usage

Headless:

```bash
pythonator --eval "2+3*4"
pythonator --eval "sqrt(16)"
pythonator --eval "200+10%"
pythonator --eval "f(x)=x^2+1; f(3)"
pythonator --eval "2+3" --json
```

Interactive:

```text
⟨ py ⟩ 2+3*4
= 14
⟨ py ⟩ f(x)=x^2+1
⟨ py ⟩ f(3)
= 10
⟨ py ⟩ stats 1 2 3 4 5
count  5
min    1
max    5
sum    15
mean   3
median 3
stddev 1.4142135623730951
```

Commands: `help`, `vars`, `funcs`, `reset`, `del <name>`, `theme [name]`, `angle rad|deg|grad`, `mode dec|hex|bin|sci`, `ms`/`mr`/`m+`/`m-`/`mc`, `stats`, `primes [n]`, `factorize <n>`, `table <expr> [a b]`, `plot <expr> [a b]`, `exit`.

## Engine

- Operators: `+`, `-`, `*`, `/`, `^`, parentheses
- Postfix `%` and `!`
- Implicit multiplication: `2x`, `2(3+4)`, `(2+3)(4+5)`
- Literals: decimal, `0x`, `0b`, `0o`
- Output radix: decimal, hex (`0xff`), binary (`0b101`) or scientific notation
- Memory slots: `ms`, `mr`, `m+`, `m-`, `mc`; the status line shows `M` while memory is live
- Built-in functions: sqrt, cbrt, sin/cos/tan and inverses, asinh/acosh/atanh, log/log2/ln/exp, abs, floor/ceil/round/sign, isprime/nextprime/prevprime, min/max, clamp, gcd/lcm, pow, mod, hypot, ncr/npr, fact
- Built-in constants: pi, tau, phi, grav, G, kB, R, NA, c, h, hbar, sigma, eps0, mu0, u, m_e, m_p, e
- User functions: `f(x)=x^2+1`
- Assignment: `x=5`

Errors return a caret marker in `--eval` mode and a readable message in the REPL.

## Development

```bash
make check
```

`unittest` covers the parser, evaluator and constants. The CLI is stdlib-only and intentionally has no third-party dependencies.

## Related

- [Plusalator](https://github.com/Mark44928/Plusalator) — the original C++17 implementation
- [GrubBlastersHTML](https://github.com/Mark44928/GrubBlastersHTML), [SnakTUI](https://github.com/Mark44928/SnakTUI), [CalculaHTML](https://github.com/Mark44928/CalculaHTML) — more from the same family
