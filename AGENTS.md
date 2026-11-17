# Pythonator

Python rewrite of Plusalator using only the standard library.

## Invariants

- No dependencies. Use the Python standard library only.
- No `eval()` or `exec()` in the engine. Parsing and evaluation are explicit.
- `python -m pythonator --eval "2+3*4"` is the machine interface and must stay stable.
- `make check` must run the test suite and a headless CLI smoke test.
- New numeric functions belong in `pythonator/engine.py`; CLI-only commands belong in `pythonator/__main__.py`.
- `tests/test_parity.py` always checks the shared expression corpus; when `PLUSALATOR_BIN` (or `../Plusalator/plusalator`) exists, it also compares the C++ engine directly.

## Commands

```bash
make check
python -m unittest discover -s tests -q
python -m pythonator --eval "2+3*4"
```
