"""Tests for House of Commons ingestion service."""

import pytest
import httpx

from canpoli.exceptions import IngestionError
from canpoli.services.hoc_ingestion import HoCIngestionService


class DummyResponse:
    def __init__(self, text, exc=None):
        self.text = text
        self._exc = exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc


@pytest.mark.asyncio
async def test_fetch_all_mps_success(monkeypatch):
    xml = """
    <Members>
      <MemberOfParliament>
        <PersonId>123</PersonId>
        <PersonOfficialFirstName>Jane</PersonOfficialFirstName>
        <PersonOfficialLastName>Doe</PersonOfficialLastName>
        <PersonEmail>jane@example.com</PersonEmail>
        <PersonTelephone>555-1212</PersonTelephone>
        <ConstituencyName>Test Riding</ConstituencyName>
        <ConstituencyProvinceTerritoryName>Ontario</ConstituencyProvinceTerritoryName>
        <CaucusShortName>Liberal</CaucusShortName>
      </MemberOfParliament>
      <MemberOfParliament>
        <PersonId>0</PersonId>
      </MemberOfParliament>
    </Members>
    """

    service = HoCIngestionService()

    async def _get(_path):
        return DummyResponse(xml)

    monkeypatch.setattr(service.client, "get", _get)

    mps = await service.fetch_all_mps()
    await service.close()

    assert len(mps) == 1
    mp = mps[0]
    assert mp["hoc_id"] == 123
    assert mp["name"] == "Jane Doe"
    assert mp["email"] == "jane@example.com"
    assert mp["party"] == "Liberal"
    assert mp["photo_url"].endswith("/123/photo")


@pytest.mark.asyncio
async def test_fetch_all_mps_http_error(monkeypatch):
    service = HoCIngestionService()

    async def _get(_path):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(service.client, "get", _get)

    with pytest.raises(IngestionError):
        await service.fetch_all_mps()

    await service.close()


@pytest.mark.asyncio
async def test_fetch_all_mps_invalid_xml(monkeypatch):
    service = HoCIngestionService()

    async def _get(_path):
        return DummyResponse("<not-xml>")

    monkeypatch.setattr(service.client, "get", _get)

    with pytest.raises(IngestionError):
        await service.fetch_all_mps()

    await service.close()
