PYTHON ?= python
PREFIX ?= $(shell if [ -n "$$TERMUX_VERSION" ]; then echo "$$PREFIX"; elif [ -n "$$HOME" ]; then echo "$$HOME/.local"; fi)

.PHONY: help check test eval install uninstall

help:
	@echo "make check     run all tests"
	@echo "make test      run the unittest suite"
	@echo "make eval      run a headless smoke test"
	@echo "make install   pip install into $(PREFIX)"
	@echo "make uninstall pip uninstall"

check: test eval

test:
	$(PYTHON) -m unittest discover -s tests -q

eval:
	$(PYTHON) -m pythonator --eval "2+3*4"

install:
	$(PYTHON) -m pip install .

uninstall:
	$(PYTHON) -m pip uninstall -y pythonator
