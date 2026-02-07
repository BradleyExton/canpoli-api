"""
CLI script for ingesting House of Commons data.

Usage:
    python -m canpoli.cli.ingest
"""

import asyncio

from canpoli.services import HoCIngestionService


async def main():
    """Run the ingestion service."""
    print("Starting House of Commons data ingestion...")

    service = HoCIngestionService()
    stats = await service.ingest()

    print("\nIngestion complete:")
    print(f"  Created: {stats['created']}")
    print(f"  Updated: {stats['updated']}")
    print(f"  Errors:  {stats['errors']}")


if __name__ == "__main__":
    asyncio.run(main())
