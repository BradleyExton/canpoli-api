# Civic Context API

Canadian political data aggregation API. Returns elected representatives (federal, provincial, municipal) for a given geographic location.

## Live API

The API is deployed at: `https://api.canpoli.dev`

## Features

- **Location-based lookup**: Get representatives by latitude/longitude
- **Multi-level government**: Returns federal (MP), provincial (MLA/MPP/MNA), and municipal representatives
- **Caching**: DynamoDB-backed caching to reduce API calls
- **AWS Lambda**: Serverless deployment via AWS Lambda + API Gateway

## API Endpoints

### Health Check

```
GET /health/
```

Returns `{"status": "ok"}` if the API is running.

### Get Civic Context

```
GET /civic/?lat={latitude}&lng={longitude}
```

**Parameters:**

- `lat` (required): Latitude (-90 to 90)
- `lng` (required): Longitude (-180 to 180)

**Example:**

```bash
curl "https://api.canpoli.dev/civic/?lat=45.4215&lng=-75.6972"
```

**Response:**

```json
{
  "representatives": {
    "federal": {
      "name": "John Doe",
      "party": "Liberal Party",
      "riding": "Ottawa Centre",
      "email": "john.doe@parl.gc.ca"
    },
    "provincial": {
      "name": "Jane Smith",
      "party": "Ontario Liberal Party",
      "riding": "Ottawa Centre",
      "email": "jane.smith@ola.org"
    },
    "municipal": {
      "name": "Bob Wilson",
      "party": null,
      "riding": "Ward 14",
      "email": "bob.wilson@ottawa.ca"
    }
  },
  "location": {
    "lat": 45.4215,
    "lng": -75.6972
  }
}
```

## Development

### Prerequisites

- Python 3.12+
- Poetry
- Node.js (for Serverless Framework deployment)
- AWS CLI configured (for deployment)

### Setup

1. Clone the repository:

```bash
git clone https://github.com/BradleyExton/canpoli-api.git
cd canpoli-api
```

2. Install Python dependencies:

```bash
poetry install
```

3. Copy environment file:

```bash
cp .env.example .env
```

4. Run locally:

```bash
make dev
```

The API will be available at `http://localhost:8000`.

### Commands

| Command          | Description                    |
| ---------------- | ------------------------------ |
| `make dev`       | Run local development server   |
| `make lint`      | Run Ruff linter                |
| `make format`    | Format code with Ruff          |
| `make typecheck` | Run mypy type checker          |
| `make test`      | Run pytest                     |
| `make check`     | Run lint, typecheck, and test  |

### Running Tests

```bash
poetry run pytest -v
```

### Linting and Type Checking

```bash
# Lint
poetry run ruff check api/

# Format
poetry run ruff format api/

# Type check
poetry run mypy api/
```

## Deployment

### Prerequisites

1. Install Serverless Framework:

```bash
npm install
```

2. Configure AWS credentials:

```bash
aws configure
```

3. Create DynamoDB table:

```bash
aws dynamodb create-table \
  --table-name civic-context-cache \
  --attribute-definitions AttributeName=cache_key,AttributeType=S \
  --key-schema AttributeName=cache_key,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Deploy

```bash
npx serverless deploy
```

## Configuration

Configuration is managed via environment variables. See `.env.example` for available options:

| Variable                 | Default                        | Description                    |
| ------------------------ | ------------------------------ | ------------------------------ |
| `AWS_REGION`             | `us-east-1`                    | AWS region for DynamoDB        |
| `DYNAMODB_TABLE_NAME`    | `civic-context-cache`          | DynamoDB table name            |
| `REPRESENT_API_BASE_URL` | `https://represent.opennorth.ca` | Represent API URL            |
| `REPRESENT_API_TIMEOUT`  | `10.0`                         | API request timeout (seconds)  |
| `CACHE_TTL_SECONDS`      | `3600`                         | Cache TTL (1 hour)             |
| `LOG_LEVEL`              | `INFO`                         | Logging level                  |

## Data Source

This API uses the [Represent API](https://represent.opennorth.ca/) by Open North to fetch Canadian elected representative data.

## License

MIT
