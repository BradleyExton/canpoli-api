# Architecture

This service is a FastAPI application with a layered structure. The goal is to keep HTTP concerns, domain logic, and persistence separate and easy to follow.

## Modules and Responsibilities

- `canpoli/app.py` and `canpoli/main.py`: application factory and ASGI entry point.
- `canpoli/routers/`: HTTP layer (request parsing, validation, response shaping).
- `canpoli/services/`: business workflows that coordinate repositories and external APIs.
- `canpoli/repositories/`: database access and query composition.
- `canpoli/models/`: SQLAlchemy ORM models.
- `canpoli/schemas/`: Pydantic response/request schemas.
- `canpoli/cli/`: ingestion commands for data sync jobs.
- `canpoli/lambda_handler.py` and `canpoli/lambda_ingest.py`: AWS Lambda entry points.

## Dependency Direction

The dependency direction should be one-way:

```
routers -> services -> repositories -> models
routers -> schemas
services -> schemas
```

Avoid importing routers from lower layers. If a service needs a schema, prefer the schema module over router types.

## Runtime Flow (Typical Request)

1. Router validates input and dependencies (auth, rate limits, DB session).
2. Repository loads data (optionally via a service for multi-step flows).
3. Router maps ORM models to Pydantic schemas for the response.

## Ingestion Flow (CLI/Lambda)

1. `canpoli/cli/*` or `canpoli/lambda_ingest.py` runs ingestion services.
2. Services fetch from external sources (House of Commons, LEGISinfo, etc.).
3. Repositories persist normalized data to the database.

## Key Conventions

- Repository methods should be side-effect free beyond DB operations.
- Services should coordinate cross-repo and external API work.
- Routers should stay thin: validation, orchestration, serialization.
