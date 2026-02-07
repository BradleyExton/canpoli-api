"""Tests for CLI ingestion."""

import pytest

from canpoli.cli import ingest as cli_ingest


@pytest.mark.asyncio
async def test_cli_ingest_outputs_stats(monkeypatch, capsys):
    class DummyService:
        async def ingest(self):
            return {"created": 1, "updated": 2, "errors": 3}

    monkeypatch.setattr(cli_ingest, "HoCIngestionService", lambda: DummyService())

    await cli_ingest.main()

    output = capsys.readouterr().out
    assert "Starting House of Commons data ingestion" in output
    assert "Created: 1" in output
    assert "Updated: 2" in output
    assert "Errors:  3" in output
