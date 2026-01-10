from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from api.civic_context.services.represent import (
    _parse_representatives,
    get_representatives,
)


class TestParseRepresentatives:
    """Tests for the representative parsing logic."""

    def test_parse_empty_list(self):
        """Test parsing empty response."""
        result = _parse_representatives([])

        assert result.federal is None
        assert result.provincial is None
        assert result.municipal is None

    def test_parse_federal_mp(self):
        """Test parsing federal MP."""
        objects = [
            {
                "name": "John Doe",
                "party_name": "Liberal Party",
                "district_name": "Ottawa Centre",
                "elected_office": "MP",
                "email": "john.doe@parl.gc.ca",
            }
        ]

        result = _parse_representatives(objects)

        assert result.federal is not None
        assert result.federal.name == "John Doe"
        assert result.federal.party == "Liberal Party"
        assert result.federal.riding == "Ottawa Centre"
        assert result.provincial is None
        assert result.municipal is None

    def test_parse_provincial_mpp(self):
        """Test parsing Ontario MPP."""
        objects = [
            {
                "name": "Jane Smith",
                "party_name": "Ontario Liberal Party",
                "district_name": "Ottawa Centre",
                "elected_office": "MPP",
                "email": "jane.smith@ola.org",
            }
        ]

        result = _parse_representatives(objects)

        assert result.provincial is not None
        assert result.provincial.name == "Jane Smith"
        assert result.federal is None

    def test_parse_provincial_mla(self):
        """Test parsing Alberta MLA."""
        objects = [
            {
                "name": "Jim Brown",
                "party_name": "UCP",
                "district_name": "Edmonton-Centre",
                "elected_office": "MLA",
                "email": None,
            }
        ]

        result = _parse_representatives(objects)

        assert result.provincial is not None
        assert result.provincial.name == "Jim Brown"

    def test_parse_provincial_mna(self):
        """Test parsing Quebec MNA."""
        objects = [
            {
                "name": "Marie Dubois",
                "party_name": "CAQ",
                "district_name": "Montreal-Centre",
                "elected_office": "MNA",
                "email": None,
            }
        ]

        result = _parse_representatives(objects)

        assert result.provincial is not None
        assert result.provincial.name == "Marie Dubois"

    def test_parse_municipal_councillor(self):
        """Test parsing municipal councillor."""
        objects = [
            {
                "name": "Bob Wilson",
                "party_name": None,
                "district_name": "Ward 14",
                "elected_office": "Councillor",
                "email": "bob@city.ca",
            }
        ]

        result = _parse_representatives(objects)

        assert result.municipal is not None
        assert result.municipal.name == "Bob Wilson"
        assert result.municipal.party is None

    def test_parse_municipal_mayor(self):
        """Test parsing mayor."""
        objects = [
            {
                "name": "Mayor Jones",
                "party_name": None,
                "district_name": "Ottawa",
                "elected_office": "Mayor",
                "email": "mayor@ottawa.ca",
            }
        ]

        result = _parse_representatives(objects)

        assert result.municipal is not None
        assert result.municipal.name == "Mayor Jones"

    def test_parse_all_levels(self):
        """Test parsing representatives at all levels."""
        objects = [
            {
                "name": "Fed Rep",
                "party_name": "P1",
                "district_name": "D1",
                "elected_office": "MP",
                "email": None,
            },
            {
                "name": "Prov Rep",
                "party_name": "P2",
                "district_name": "D2",
                "elected_office": "MPP",
                "email": None,
            },
            {
                "name": "Muni Rep",
                "party_name": None,
                "district_name": "D3",
                "elected_office": "Councillor",
                "email": None,
            },
        ]

        result = _parse_representatives(objects)

        assert result.federal.name == "Fed Rep"
        assert result.provincial.name == "Prov Rep"
        assert result.municipal.name == "Muni Rep"


@pytest.mark.asyncio
class TestGetRepresentatives:
    """Tests for the API call to Represent."""

    async def test_get_representatives_success(self):
        """Test successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "objects": [
                {
                    "name": "Test Rep",
                    "party_name": "Test Party",
                    "district_name": "Test District",
                    "elected_office": "MP",
                    "email": "test@test.com",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch(
            "api.civic_context.services.represent.httpx.AsyncClient"
        ) as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await get_representatives(45.4215, -75.6972)

        assert result.federal is not None
        assert result.federal.name == "Test Rep"

    async def test_get_representatives_timeout(self):
        """Test timeout raises HTTPException with 504."""
        with patch(
            "api.civic_context.services.represent.httpx.AsyncClient"
        ) as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.TimeoutException("timeout")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_representatives(45.4215, -75.6972)

            assert exc_info.value.status_code == 504

    async def test_get_representatives_server_error(self):
        """Test 5xx errors raise HTTPException with 503."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch(
            "api.civic_context.services.represent.httpx.AsyncClient"
        ) as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.HTTPStatusError(
                    "Server Error", request=MagicMock(), response=mock_response
                )
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_representatives(45.4215, -75.6972)

            assert exc_info.value.status_code == 503

    async def test_get_representatives_connection_error(self):
        """Test connection errors raise HTTPException with 502."""
        with patch(
            "api.civic_context.services.represent.httpx.AsyncClient"
        ) as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.ConnectError("Connection refused")
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_representatives(45.4215, -75.6972)

            assert exc_info.value.status_code == 502
