# Contributing

Thanks for helping improve CanPoli API. This guide focuses on making contributions easy to review and easy to maintain.

## Setup

```bash
poetry install
cp .env.example .env
docker-compose up -d
poetry run alembic upgrade head
```

## Common Commands

```bash
poetry run pytest
poetry run ruff check .
poetry run ruff format .
poetry run mypy canpoli
```

If you have GNU Make installed:

```bash
make setup
make dev
make test
make lint
make format
make typecheck
```

## Pre-commit Hooks

```bash
poetry run pre-commit install
```

## Branching and PRs

- Create a focused branch per change.
- Keep PRs small and scoped.
- Update or add tests when behavior changes.
- Update docs when you change configuration or workflows.

## PR Checklist

- [ ] Tests pass (`pytest`)
- [ ] Lint and format checks pass (`ruff`)
- [ ] Type checks pass (`mypy`)
- [ ] Docs updated (if behavior/config changed)

## Style

- Ruff for linting and formatting
- Mypy for type checks
- Prefer small, composable functions
- Keep routers thin, move workflows into services
