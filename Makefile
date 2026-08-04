VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
RUFF=$(VENV)/bin/ruff
BLACK=$(VENV)/bin/black
PYTEST=$(VENV)/bin/pytest
UVICORN=$(VENV)/bin/uvicorn

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

example:
	PYTHONPATH=src $(PY) examples/001_create_world.py

serve:
	PYTHONPATH=src $(UVICORN) living_world.api.server:app --reload

clean:
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
