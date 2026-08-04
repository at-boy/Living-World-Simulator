PYTHON=python3

install:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && pip install -e .[dev]

test:
	pytest

lint:
	ruff check src tests

format:
	black src tests

check: lint test

example:
	$(PYTHON) examples/001_create_world.py

serve:
	uvicorn living_world.api.server:app --reload
