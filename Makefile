.PHONY: all fix check examples clean

VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
RUFF=$(VENV)/bin/ruff
BLACK=$(VENV)/bin/black
PYTEST=$(VENV)/bin/pytest
UVICORN=$(VENV)/bin/uvicorn

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
	@echo "Running Living World examples..."
	@echo

	@echo "=================================================="
	@echo "001_create_world.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/001_create_world.py
	@echo

	@echo "=================================================="
	@echo "002_definitions.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/002_definitions.py
	@echo

	@echo "=================================================="
	@echo "003_scheduler.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/003_scheduler.py
	@echo

	@echo "=================================================="
	@echo "004_engine.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/004_engine.py
	@echo

	@echo "=================================================="
	@echo "005_resource_definitions.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/005_resource_definitions.py
	@echo

	@echo "=================================================="
	@echo "006_resources.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/006_resources.py
	@echo

	@echo "=================================================="
	@echo "007_resource_operations.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/007_resource_operations.py
	@echo

	@echo "=================================================="
	@echo "008_observations.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/008_observations.py
	@echo

	@echo "=================================================="
	@echo "009_beliefs.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/009_beliefs.py
	@echo

	@echo "=================================================="
	@echo "010_experiences.py"
	@echo "=================================================="
	@PYTHONPATH=src .venv/bin/python examples/010_experiences.py

serve:
	PYTHONPATH=src $(UVICORN) living_world.api.server:app --reload

clean:
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
