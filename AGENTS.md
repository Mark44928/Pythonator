# Pythonator

Python rewrite of Plusalator using only the standard library.

## Invariants

- No dependencies. Use the Python standard library only.
- No `eval()` or `exec()` in the engine. Parsing and evaluation are explicit.
- `python -m pythonator --eval "2+3*4"` is the machine interface and must stay stable.
- `make check` must run the test suite and a headless CLI smoke test.
- New numeric functions belong in `pythonator/engine.py`; CLI-only commands belong in `pythonator/__main__.py`.

## Commands

```bash
make check
python -m unittest discover -s tests -q
python -m pythonator --eval "2+3*4"
```
