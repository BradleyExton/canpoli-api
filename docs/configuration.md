# Configuration

Configuration is loaded via `canpoli.config.Settings` (Pydantic) from environment variables. The defaults live in `canpoli/config.py`, and `.env.example` documents typical local values.

## Database

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | None | PostgreSQL async URL, e.g. `postgresql+asyncpg://user:pass@host:port/db`. |
| `DATABASE_POOL_SIZE` | No | 5 | Pool size for non-Lambda environments. |
| `DATABASE_MAX_OVERFLOW` | No | 10 | Additional pool connections. |
| `DATABASE_POOL_TIMEOUT` | No | 30 | Seconds to wait for a pool connection. |
| `DATABASE_POOL_RECYCLE` | No | 1800 | Seconds before recycling connections. |
| `DATABASE_ECHO` | No | false | Log SQL statements when true. |

## House of Commons / Parliamentary Ingestion

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `HOC_API_BASE_URL` | No | `https://www.ourcommons.ca` | Base URL for House of Commons API. |
| `HOC_API_TIMEOUT` | No | 10.0 | HTTP timeout in seconds. |
| `HOC_PARLIAMENT` | No | 45 | Parliament number. |
| `HOC_SESSION` | No | 1 | Session number. |
| `HOC_MAX_CONCURRENCY` | No | 4 | Max concurrent HTTP requests. |
| `HOC_MIN_REQUEST_INTERVAL_MS` | No | 250 | Throttle between requests. |
| `HOC_DEBATES_MAX_SITTING` | No | 200 | Max sitting number for debates. |
| `HOC_DEBATES_LOOKAHEAD` | No | 10 | Lookahead for debates. |
| `HOC_DEBATES_MAX_MISSING` | No | 20 | Max missing debates before stop. |
| `HOC_DEBATE_LANGUAGES` | No | `['en','fr']` | Languages to ingest. |
| `HOC_ENABLE_ROLES` | No | true | Toggle roles ingestion. |
| `HOC_ENABLE_PARTY_STANDINGS` | No | true | Toggle party standings ingestion. |
| `HOC_ENABLE_VOTES` | No | true | Toggle votes ingestion. |
| `HOC_ENABLE_PETITIONS` | No | true | Toggle petitions ingestion. |
| `HOC_ENABLE_DEBATES` | No | true | Toggle debates ingestion. |
| `HOC_ENABLE_EXPENDITURES` | No | true | Toggle expenditures ingestion. |
| `HOC_ENABLE_BILLS` | No | true | Toggle bills ingestion. |

## CORS

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `CORS_ORIGINS` | No | `[]` | JSON list of allowed origins. Empty list enables permissive dev CORS. |

Example:

```bash
CORS_ORIGINS='["https://canpoli.dev","https://app.canpoli.dev"]'
```

## Rate Limiting and Usage

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `FREE_RATE_LIMIT_PER_MINUTE` | No | 50 | Requests/minute for free tier (by IP). |
| `PAID_RATE_LIMIT_PER_MINUTE` | No | 500 | Requests/minute for paid tier (by API key). |
| `REDIS_URL` | No | None | Required outside dev/test for rate limiting and usage tracking. |

## API Keys

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `API_KEY_HMAC_SECRET` | No | None | Required to hash/generate API keys. |

## Stripe Billing

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `STRIPE_SECRET_KEY` | No | None | Stripe API key. |
| `STRIPE_WEBHOOK_SECRET` | No | None | Webhook signing secret. |
| `STRIPE_PRICE_ID` | No | None | Subscription price ID. |
| `STRIPE_CHECKOUT_SUCCESS_URL` | No | None | Redirect after checkout. |
| `STRIPE_CHECKOUT_CANCEL_URL` | No | None | Cancel redirect. |
| `STRIPE_PORTAL_RETURN_URL` | No | None | Billing portal return URL. |

## Clerk Auth

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `CLERK_JWKS_URL` | No | None | JWKS URL from Clerk. |
| `CLERK_ISSUER` | No | None | Token issuer. |
| `CLERK_AUDIENCE` | No | None | Token audience. |

## Sentry

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `SENTRY_DSN` | No | None | Enable error tracking when set. |
| `SENTRY_ENVIRONMENT` | No | None | Environment name. |
| `SENTRY_RELEASE` | No | None | Release identifier. |
| `SENTRY_SEND_DEFAULT_PII` | No | false | Send PII when true. |
| `SENTRY_TRACES_SAMPLE_RATE` | No | None | Set to enable tracing. |

## Application

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `ENVIRONMENT` | No | development | Used to toggle dev/test behavior. |
| `DEBUG` | No | false | Enables debug mode. |
| `LOG_LEVEL` | No | INFO | Logging level. |

## Lambda Ingestion

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `ENABLE_PARLIAMENT_INGEST` | No | false | Enable parliamentary ingestion in Lambda. |
| `BOUNDARY_GEOJSON_URL` | No | None | Optional URL for boundary refresh. |
