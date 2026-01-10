# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

| Command | Description |
|---------|-------------|
| `make dev` | Run local dev server (http://localhost:8000) |
| `make lint` | Run Ruff linter |
| `make format` | Format code with Ruff |
| `make typecheck` | Run mypy |
| `make test` | Run pytest |
| `make check` | Run lint, typecheck, and test |

Run a single test:
```bash
poetry run pytest api/tests/test_civic.py::test_function_name -v
```

## Architecture

This is a FastAPI application that returns Canadian elected representatives (federal, provincial, municipal) for a given lat/lng coordinate. Deployed as AWS Lambda via Serverless Framework.

### Code Organization

```
api/civic_context/
├── main.py              # FastAPI app initialization
├── handler.py           # AWS Lambda entry point (Mangum adapter)
├── config.py            # Pydantic Settings configuration
├── routers/
│   ├── civic/
│   │   ├── router.py    # GET /civic/?lat=&lng= endpoint
│   │   └── models.py    # Request/response Pydantic models
│   └── health/
│       └── router.py    # GET /health/ endpoint
├── services/
│   └── represent.py     # External API client (represent.opennorth.ca)
└── db/
    └── cache.py         # DynamoDB cache layer
```

### Request Flow

1. Router receives request with lat/lng query params
2. Check DynamoDB cache (key: rounded coordinates to 4 decimal places)
3. On cache miss: fetch from Represent API, parse by government level
4. Store response in cache with TTL
5. Return `CivicContextResponse` with representatives and location

### Key Patterns

- **Async throughout**: httpx for HTTP calls, boto3 for DynamoDB
- **Graceful cache failures**: cache errors are logged but don't fail requests
- **HTTP error mapping**: timeout→504, upstream 5xx→502/503
- **Router organization**: each feature has its own directory with router.py and models.py
