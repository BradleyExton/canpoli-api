# CanPoli API

Canadian Political Data API - Federal MPs, Ridings, and Parties.

## Setup

### Prerequisites

- Python 3.12+
- Poetry
- Docker (for PostgreSQL + PostGIS)

### Installation

```bash
# Clone and enter directory
cd ~/projects/canpoli-api

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Start PostgreSQL + Redis
docker-compose up -d

# Run database migrations
poetry run alembic upgrade head

# Ingest data from House of Commons
poetry run python -m canpoli.cli.ingest

# Ingest parliamentary data (roles, votes, bills, petitions, debates, expenditures)
poetry run python -m canpoli.cli.ingest_parliament

# Ingest riding boundaries (GeoJSON) for lat/lng lookup
poetry run python -m canpoli.cli.ingest_boundaries --geojson /path/to/boundaries.geojson

# Start development server
poetry run uvicorn canpoli.main:app --reload
```

## Quickstart (10 minutes)

```bash
poetry install
cp .env.example .env
docker-compose up -d
poetry run alembic upgrade head
poetry run python -m canpoli.cli.ingest
poetry run uvicorn canpoli.main:app --reload
```

Smoke test:

```bash
curl http://localhost:8000/health
```

If you have GNU Make installed, you can use `make setup` and `make dev` instead. See `docs/development.md`.

## Architecture (High Level)

Layered modules with one-way dependencies:

- Routers -> Services -> Repositories -> Models
- Routers -> Schemas

See `docs/architecture.md` for details.

## Ingestion Overview

- `canpoli.cli.ingest`: core HoC data (representatives, ridings, parties).
- `canpoli.cli.ingest_parliament`: roles, votes, bills, petitions, debates, expenditures.
- `canpoli.cli.ingest_boundaries`: PostGIS riding boundaries for coordinate lookup.

See `docs/ingestion.md` for when to run each flow and Lambda options.

## Configuration

Configuration is managed in `canpoli/config.py` and loaded from environment variables.
See `docs/configuration.md` for a full reference (including `CORS_ORIGINS` JSON list format).

## Docs

- `docs/architecture.md`
- `docs/development.md`
- `docs/configuration.md`
- `docs/ingestion.md`
- `docs/deployment.md`

## API Endpoints

### Health
- `GET /health` - API and database status

### Account (requires Clerk JWT)
- `GET /v1/account/api-key` - Get masked API key (may include one-time reveal)
- `POST /v1/account/api-key/rotate` - Rotate API key
- `GET /v1/account/usage` - Usage for current billing period

### Billing (requires Clerk JWT except webhook)
- `POST /v1/billing/checkout` - Create Stripe Checkout session
- `POST /v1/billing/portal` - Create Stripe Billing Portal session
- `POST /v1/billing/webhook` - Stripe webhook endpoint

### Representatives
- `GET /v1/representatives` - Paginated list of representatives
  - Query params: `province`, `party`, `limit`, `offset`
- `GET /v1/representatives/{hoc_id}` - Single representative by House of Commons ID
- `GET /v1/representatives/lookup` - Lookup by postal code or coordinates
  - Postal code lookup not yet implemented
  - Lat/lng lookup requires PostGIS and riding boundary ingestion

### Ridings
- `GET /v1/ridings` - Paginated list of ridings
  - Query params: `province`, `limit`, `offset`
- `GET /v1/ridings/{id}` - Single riding with current representative

### Parties
- `GET /v1/parties` - All political parties
  - Query params: `include_standings`, `parliament`, `session_number`

### Roles
- `GET /v1/roles` - Roles list
  - Query params: `hoc_id`, `current`, `role_type`, `parliament`, `session_number`, `limit`, `offset`
- `GET /v1/roles/representatives/{hoc_id}` - Roles for a representative

### Party Standings
- `GET /v1/party-standings` - Latest party seat counts
  - Query params: `parliament`, `session_number`, `as_of_date`, `limit`, `offset`

### Bills
- `GET /v1/bills` - Bills list
  - Query params: `bill_number`, `status`, `sponsor_hoc_id`, `updated_since`, `parliament`, `session_number`, `limit`, `offset`
- `GET /v1/bills/{bill_id}` - Bill detail

### Votes
- `GET /v1/votes` - Votes list
  - Query params: `date`, `decision`, `bill_number`, `parliament`, `session_number`, `include_members`, `limit`, `offset`
- `GET /v1/votes/{vote_id}` - Vote detail (includes members by default)

### Petitions
- `GET /v1/petitions` - Petitions list
  - Query params: `status`, `sponsor_hoc_id`, `from_date`, `to_date`, `parliament`, `session_number`, `limit`, `offset`
- `GET /v1/petitions/{petition_id}` - Petition detail

### Debates
- `GET /v1/debates` - Debates list
  - Query params: `date`, `language`, `sitting`, `parliament`, `session_number`, `limit`, `offset`
- `GET /v1/debates/{debate_id}` - Debate detail
  - Query params: `include_interventions`

### Expenditures
- `GET /v1/expenditures/members` - Member expenditures list
  - Query params: `fiscal_year`, `category`, `limit`, `offset`
- `GET /v1/expenditures/members/{hoc_id}` - Expenditures for a member
  - Query params: `fiscal_year`, `category`, `limit`, `offset`
- `GET /v1/expenditures/house-officers` - House officer expenditures
  - Query params: `fiscal_year`, `category`, `limit`, `offset`

Unversioned routes are also available for backwards compatibility.

## Development

```bash
# Run tests
poetry run pytest

# Run PostGIS integration tests (requires local PostGIS)
# These use POSTGIS_TEST_DATABASE_URL to target the PostGIS service.
POSTGIS_TEST_DATABASE_URL=postgresql+asyncpg://canpoli:canpoli_dev@localhost:5433/canpoli_test \
  poetry run pytest -m integration

# Lint
poetry run ruff check .

# Format
poetry run ruff format .

# Type check
poetry run mypy canpoli
```

## Sentry

Set at minimum `SENTRY_DSN` to enable error tracking. Optional settings include
`SENTRY_ENVIRONMENT`, `SENTRY_RELEASE`, `SENTRY_SEND_DEFAULT_PII`, and
`SENTRY_TRACES_SAMPLE_RATE` (leave empty to keep tracing disabled).

To verify locally, run the API with `SENTRY_DSN` set and trigger an exception
in a route; the event should appear in Sentry.

## Rate Limits

- Free: 50 req/min by IP (no API key needed)
- Paid: 500 req/min by API key (`X-API-Key`)

## Data Source

MP data is sourced from the House of Commons Open Data API and LEGISinfo (for bills), along with House of Commons votes, petitions, Hansard debates, and proactive disclosure feeds.
