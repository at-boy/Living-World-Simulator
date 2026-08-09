.PHONY: all fix check examples clean

VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
RUFF=$(VENV)/bin/ruff
BLACK=$(VENV)/bin/black
PYTEST=$(VENV)/bin/pytest
UVICORN=$(VENV)/bin/uvicorn
EXAMPLES=$(sort $(wildcard examples/[0-9][0-9][0-9]_*.py))

all: fix check examples

install:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"

fix:
	$(RUFF) check --fix src tests
	$(BLACK) src tests

lint:
	$(RUFF) check src tests

format-check:
	$(BLACK) --check src tests

test:
	PYTHONPATH=src $(PYTEST)

check: lint format-check test

examples:
	@set -e; \
	for example in $(EXAMPLES); do \
		printf 'Running %s\n' "$$example"; \
		if PYTHONPATH=src $(PY) "$$example"; then \
			printf 'PASS %s\n\n' "$$example"; \
		else \
			status=$$?; \
			printf 'FAIL %s\n' "$$example" >&2; \
			exit $$status; \
		fi; \
	done

serve:
	PYTHONPATH=src $(UVICORN) living_world.api.server:app --reload

clean:
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
