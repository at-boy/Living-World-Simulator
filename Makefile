VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
BLACK := $(VENV)/bin/black
UVICORN := $(VENV)/bin/uvicorn

install:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"

test:
	$(PYTEST)

lint:
	$(RUFF) check src tests

format:
	$(BLACK) src tests

check: lint test

example:
	$(PYTHON) examples/001_create_world.py

serve:
	$(UVICORN) living_world.api.server:app --reload

clean:
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info

release: check
	@echo "Release checks passed."
