"""
CLI script for ingesting House of Commons parliamentary data.

Usage:
    python -m canpoli.cli.ingest_parliament
    python -m canpoli.cli.ingest_parliament --only votes,debates
"""

import argparse
import asyncio

from canpoli.services.hoc_parliament_ingestion import HoCParliamentIngestionService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest parliamentary data")
    parser.add_argument(
        "--only",
        help="Comma-separated list of pipelines to run (roles,party_standings,votes,petitions,debates,expenditures,bills)",
        default=None,
    )
    args = parser.parse_args()

    service = HoCParliamentIngestionService()
    try:
        if args.only:
            pipelines = {p.strip() for p in args.only.split(",") if p.strip()}
            stats = {}
            if "party_standings" in pipelines:
                stats["party_standings"] = await service.ingest_party_standings()
            if "roles" in pipelines:
                stats["roles"] = await service.ingest_roles()
            if "votes" in pipelines:
                stats["votes"] = await service.ingest_votes()
            if "petitions" in pipelines:
                stats["petitions"] = await service.ingest_petitions()
            if "debates" in pipelines:
                stats["debates"] = await service.ingest_debates()
            if "expenditures" in pipelines:
                stats["expenditures"] = await service.ingest_expenditures()
            if "bills" in pipelines:
                stats["bills"] = await service.ingest_bills()
        else:
            stats = await service.ingest()

        print("Ingestion complete:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
