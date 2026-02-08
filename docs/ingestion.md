# Data Ingestion

The API relies on external sources (House of Commons and LEGISinfo) to populate the database. Ingestion is run via CLI locally or scheduled in AWS Lambda.

## Commands

### Core HoC ingestion (MPs and related base data)

```bash
poetry run python -m canpoli.cli.ingest
```

### Parliamentary data (roles, votes, bills, petitions, debates, expenditures)

```bash
poetry run python -m canpoli.cli.ingest_parliament
```

### Riding boundary ingestion (PostGIS lookup support)

```bash
poetry run python -m canpoli.cli.ingest_boundaries --geojson /path/to/boundaries.geojson
```

## When to Run

- Run `ingest` after initial DB setup to seed representatives, ridings, and parties.
- Run `ingest_parliament` to populate legislative data and keep it current.
- Run `ingest_boundaries` when you need coordinate lookup (`/representatives/lookup`).

Ingestion can take several minutes depending on network latency and data volume.

## Lambda Scheduled Ingestion

`canpoli/lambda_ingest.py` is deployed as a scheduled Lambda. It runs the core HoC ingestion daily and can optionally:

- Include parliamentary ingestion via `ENABLE_PARLIAMENT_INGEST=true`.
- Refresh boundaries by setting `BOUNDARY_GEOJSON_URL` to a GeoJSON URL.

See `docs/configuration.md` for the full list of settings.

## Data Sources

- House of Commons Open Data API (MPs, roles, standings, etc.)
- LEGISinfo (bills)
- House of Commons votes, petitions, Hansard debates
- Proactive disclosure feeds (expenditures)
