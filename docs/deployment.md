# Deployment

The project ships with Serverless Framework configuration for AWS Lambda + API Gateway.

## Serverless

- Entry point: `canpoli/lambda_handler.py`
- Scheduled ingestion: `canpoli/lambda_ingest.py`
- Config: `serverless.yml`

Key deployment settings in `serverless.yml`:

- Environment variables are pulled from AWS SSM/Secrets Manager.
- VPC settings are required for RDS access.
- CloudWatch alarms are defined for Lambda errors.

## Local Docker

Local Postgres + PostGIS + Redis are defined in `docker-compose.yml` for development and testing.

## Notes

- Ensure the database URL is configured in Secrets Manager before deploying.
- If running in Lambda, connection pooling is disabled to avoid stale connections.
