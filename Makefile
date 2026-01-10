.PHONY: dev lint format typecheck test

dev:
	poetry run uvicorn api.civic_context.main:app --reload

lint:
	poetry run ruff check api/

format:
	poetry run ruff format api/
	poetry run ruff check --fix api/

typecheck:
	poetry run mypy api/

test:
	poetry run pytest

check: lint typecheck test