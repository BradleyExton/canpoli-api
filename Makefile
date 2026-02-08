SHELL := /bin/bash

POETRY := poetry
APP := canpoli.main:app
GEOJSON ?=

.PHONY: setup dev test lint format typecheck migrate ingest ingest-parliament ingest-boundaries

setup:
	$(POETRY) install
	cp -n .env.example .env || true

dev:
	$(POETRY) run uvicorn $(APP) --reload

test:
	$(POETRY) run pytest

lint:
	$(POETRY) run ruff check .

format:
	$(POETRY) run ruff format .

typecheck:
	$(POETRY) run mypy canpoli

migrate:
	$(POETRY) run alembic upgrade head

ingest:
	$(POETRY) run python -m canpoli.cli.ingest

ingest-parliament:
	$(POETRY) run python -m canpoli.cli.ingest_parliament

ingest-boundaries:
	@if [ -z "$(GEOJSON)" ]; then \
		echo "GEOJSON is required. Example: make ingest-boundaries GEOJSON=/path/to/boundaries.geojson"; \
		exit 1; \
	fi
	$(POETRY) run python -m canpoli.cli.ingest_boundaries --geojson $(GEOJSON)
