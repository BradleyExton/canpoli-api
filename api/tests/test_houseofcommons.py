"""Tests for House of Commons API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.civic_context.services.houseofcommons import (
    _fetch_all_mps,
    _fetch_ministers,
    _fetch_mp_details,
    _fetch_parliamentary_secretaries,
    _normalize_constituency,
    get_house_of_commons_data,
)


class TestNormalizeConstituency:
    """Tests for constituency name normalization."""

    def test_normalize_simple(self):
        """Test simple constituency name."""
        assert _normalize_constituency("Ottawa Centre") == "ottawa centre"

    def test_normalize_em_dash(self):
        """Test constituency with em-dash."""
        assert _normalize_constituency("Saint-Maurice—Champlain") == "saint-maurice-champlain"

    def test_normalize_en_dash(self):
        """Test constituency with en-dash."""
        assert _normalize_constituency("Saint-Maurice–Champlain") == "saint-maurice-champlain"

    def test_normalize_hyphen(self):
        """Test constituency with regular hyphen."""
        assert _normalize_constituency("Saint-Maurice-Champlain") == "saint-maurice-champlain"

    def test_normalize_whitespace(self):
        """Test constituency with leading/trailing whitespace."""
        assert _normalize_constituency("  Ottawa Centre  ") == "ottawa centre"


@pytest.mark.asyncio
class TestFetchAllMPs:
    """Tests for MP list fetching."""

    async def test_fetch_mps_success(self):
        """Test successful MP list fetching."""
        xml_response = """
        <ArrayOfMemberOfParliament>
            <MemberOfParliament>
                <PersonId>12345</PersonId>
                <PersonShortHonorific>Hon.</PersonShortHonorific>
                <PersonOfficialFirstName>John</PersonOfficialFirstName>
                <PersonOfficialLastName>Doe</PersonOfficialLastName>
                <ConstituencyName>Ottawa Centre</ConstituencyName>
                <ConstituencyProvinceTerritoryName>Ontario</ConstituencyProvinceTerritoryName>
                <CaucusShortName>Liberal</CaucusShortName>
            </MemberOfParliament>
        </ArrayOfMemberOfParliament>
        """

        mock_response = MagicMock()
        mock_response.text = xml_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Clear cache first
        import api.civic_context.services.houseofcommons as hoc_module
        hoc_module._mp_cache = None
        hoc_module._mp_cache_expires_at = None

        result = await _fetch_all_mps(mock_client)

        assert "ottawa centre" in result
        mp_data = result["ottawa centre"]
        assert mp_data["person_id"] == 12345
        assert mp_data["honorific"] == "Hon."
        assert mp_data["first_name"] == "John"
        assert mp_data["last_name"] == "Doe"
        assert mp_data["constituency"] == "Ottawa Centre"
        assert mp_data["province"] == "Ontario"
        assert mp_data["caucus"] == "Liberal"

    async def test_fetch_mps_multiple(self):
        """Test fetching multiple MPs."""
        xml_response = """
        <ArrayOfMemberOfParliament>
            <MemberOfParliament>
                <PersonId>12345</PersonId>
                <PersonOfficialFirstName>John</PersonOfficialFirstName>
                <PersonOfficialLastName>Doe</PersonOfficialLastName>
                <ConstituencyName>Ottawa Centre</ConstituencyName>
                <ConstituencyProvinceTerritoryName>Ontario</ConstituencyProvinceTerritoryName>
                <CaucusShortName>Liberal</CaucusShortName>
            </MemberOfParliament>
            <MemberOfParliament>
                <PersonId>67890</PersonId>
                <PersonOfficialFirstName>Jane</PersonOfficialFirstName>
                <PersonOfficialLastName>Smith</PersonOfficialLastName>
                <ConstituencyName>Toronto Centre</ConstituencyName>
                <ConstituencyProvinceTerritoryName>Ontario</ConstituencyProvinceTerritoryName>
                <CaucusShortName>Conservative</CaucusShortName>
            </MemberOfParliament>
        </ArrayOfMemberOfParliament>
        """

        mock_response = MagicMock()
        mock_response.text = xml_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Clear cache first
        import api.civic_context.services.houseofcommons as hoc_module
        hoc_module._mp_cache = None
        hoc_module._mp_cache_expires_at = None

        result = await _fetch_all_mps(mock_client)

        assert len(result) == 2
        assert "ottawa centre" in result
        assert "toronto centre" in result

    async def test_fetch_mps_timeout(self):
        """Test timeout returns empty dict or cached data."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        # Clear cache first
        import api.civic_context.services.houseofcommons as hoc_module
        hoc_module._mp_cache = None
        hoc_module._mp_cache_expires_at = None

        result = await _fetch_all_mps(mock_client)

        assert result == {}

    async def test_fetch_mps_invalid_xml(self):
        """Test invalid XML returns empty dict or cached data."""
        mock_response = MagicMock()
        mock_response.text = "not valid xml"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Clear cache first
        import api.civic_context.services.houseofcommons as hoc_module
        hoc_module._mp_cache = None
        hoc_module._mp_cache_expires_at = None

        result = await _fetch_all_mps(mock_client)

        assert result == {}


@pytest.mark.asyncio
class TestFetchMinisters:
    """Tests for ministers fetching."""

    async def test_fetch_ministers_success(self):
        """Test successful ministers fetching."""
        xml_response = """
        <ArrayOfCabinetMember>
            <CabinetMember>
                <PersonId>12345</PersonId>
                <Title>Minister of Finance</Title>
                <OrderOfPrecedence>3</OrderOfPrecedence>
                <FromDateTime>2024-01-15</FromDateTime>
            </CabinetMember>
        </ArrayOfCabinetMember>
        """

        mock_response = MagicMock()
        mock_response.text = xml_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Clear cache first
        import api.civic_context.services.houseofcommons as hoc_module
        hoc_module._ministers_cache = None
        hoc_module._ministers_cache_expires_at = None

        result = await _fetch_ministers(mock_client)

        assert 12345 in result
        assert result[12345].title == "Minister of Finance"
        assert result[12345].order_of_precedence == 3
        assert result[12345].from_date == "2024-01-15"

    async def test_fetch_ministers_timeout(self):
        """Test timeout returns empty dict or cached data."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        # Clear cache first
        import api.civic_context.services.houseofcommons as hoc_module
        hoc_module._ministers_cache = None
        hoc_module._ministers_cache_expires_at = None

        result = await _fetch_ministers(mock_client)

        assert result == {}


@pytest.mark.asyncio
class TestFetchParliamentarySecretaries:
    """Tests for parliamentary secretaries fetching."""

    async def test_fetch_secretaries_success(self):
        """Test successful secretaries fetching."""
        xml_response = """
        <ArrayOfParliamentarySecretary>
            <ParliamentarySecretary>
                <PersonId>67890</PersonId>
                <Title>Parliamentary Secretary to the Minister of Finance</Title>
                <FromDateTime>2024-02-01</FromDateTime>
            </ParliamentarySecretary>
        </ArrayOfParliamentarySecretary>
        """

        mock_response = MagicMock()
        mock_response.text = xml_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Clear cache first
        import api.civic_context.services.houseofcommons as hoc_module
        hoc_module._secretaries_cache = None
        hoc_module._secretaries_cache_expires_at = None

        result = await _fetch_parliamentary_secretaries(mock_client)

        assert 67890 in result
        assert result[67890].title == "Parliamentary Secretary to the Minister of Finance"
        assert result[67890].from_date == "2024-02-01"


@pytest.mark.asyncio
class TestFetchMPDetails:
    """Tests for individual MP details fetching."""

    async def test_fetch_mp_details_success(self):
        """Test successful MP details fetching."""
        xml_response = """
        <MemberOfParliament>
            <PersonId>12345</PersonId>
            <CommitteeMemberRoles>
                <CommitteeMemberRole>
                    <CommitteeName>Standing Committee on Finance</CommitteeName>
                    <Title>Member</Title>
                </CommitteeMemberRole>
            </CommitteeMemberRoles>
            <ParliamentaryAssociationsandInterparliamentaryGroupRoles>
                <ParliamentaryAssociationandInterparliamentaryGroupRole>
                    <OrganizationName>Canada-Europe Parliamentary Association</OrganizationName>
                    <Title>Member</Title>
                </ParliamentaryAssociationandInterparliamentaryGroupRole>
            </ParliamentaryAssociationsandInterparliamentaryGroupRoles>
        </MemberOfParliament>
        """

        mock_response = MagicMock()
        mock_response.text = xml_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        committees, associations = await _fetch_mp_details(mock_client, 12345)

        assert len(committees) == 1
        assert committees[0].name == "Standing Committee on Finance"
        assert committees[0].role == "Member"

        assert len(associations) == 1
        assert associations[0].name == "Canada-Europe Parliamentary Association"
        assert associations[0].role == "Member"

    async def test_fetch_mp_details_empty(self):
        """Test MP with no committees or associations."""
        xml_response = """
        <MemberOfParliament>
            <PersonId>12345</PersonId>
        </MemberOfParliament>
        """

        mock_response = MagicMock()
        mock_response.text = xml_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        committees, associations = await _fetch_mp_details(mock_client, 12345)

        assert committees == []
        assert associations == []

    async def test_fetch_mp_details_timeout(self):
        """Test timeout returns empty lists."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        committees, associations = await _fetch_mp_details(mock_client, 12345)

        assert committees == []
        assert associations == []


@pytest.mark.asyncio
class TestGetHouseOfCommonsData:
    """Tests for the main orchestration function."""

    async def test_mp_found_with_all_data(self):
        """Test complete flow with all data."""
        with patch(
            "api.civic_context.services.houseofcommons.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = MagicMock()

            # Clear caches
            import api.civic_context.services.houseofcommons as hoc_module
            hoc_module._mp_cache = None
            hoc_module._mp_cache_expires_at = None
            hoc_module._ministers_cache = None
            hoc_module._ministers_cache_expires_at = None
            hoc_module._secretaries_cache = None
            hoc_module._secretaries_cache_expires_at = None

            async def get_response(url):
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()

                if url == "/Members/en/search/XML":
                    mock_response.text = """
                    <ArrayOfMemberOfParliament>
                        <MemberOfParliament>
                            <PersonId>12345</PersonId>
                            <PersonShortHonorific>Hon.</PersonShortHonorific>
                            <PersonOfficialFirstName>John</PersonOfficialFirstName>
                            <PersonOfficialLastName>Doe</PersonOfficialLastName>
                            <ConstituencyName>Ottawa Centre</ConstituencyName>
                            <ConstituencyProvinceTerritoryName>Ontario</ConstituencyProvinceTerritoryName>
                            <CaucusShortName>Liberal</CaucusShortName>
                        </MemberOfParliament>
                    </ArrayOfMemberOfParliament>
                    """
                elif url == "/Members/en/ministries/XML":
                    mock_response.text = """
                    <ArrayOfCabinetMember>
                        <CabinetMember>
                            <PersonId>12345</PersonId>
                            <Title>Minister of Finance</Title>
                            <OrderOfPrecedence>3</OrderOfPrecedence>
                            <FromDateTime>2024-01-15</FromDateTime>
                        </CabinetMember>
                    </ArrayOfCabinetMember>
                    """
                elif url == "/Members/en/parliamentary-secretaries/XML":
                    mock_response.text = "<ArrayOfParliamentarySecretary></ArrayOfParliamentarySecretary>"
                elif url == "/Members/en/12345/XML":
                    mock_response.text = """
                    <MemberOfParliament>
                        <PersonId>12345</PersonId>
                        <CommitteeMemberRoles>
                            <CommitteeMemberRole>
                                <CommitteeName>Finance</CommitteeName>
                                <Title>Chair</Title>
                            </CommitteeMemberRole>
                        </CommitteeMemberRoles>
                    </MemberOfParliament>
                    """
                else:
                    mock_response.text = "<Empty/>"

                return mock_response

            mock_client.get = AsyncMock(side_effect=get_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await get_house_of_commons_data("Ottawa Centre")

            assert result is not None
            assert result.hoc_person_id == 12345
            assert result.honorific == "Hon."
            assert result.province == "Ontario"
            assert result.photo_url == "https://www.ourcommons.ca/Members/en/12345/photo"
            assert result.profile_url == "https://www.ourcommons.ca/Members/en/12345"
            assert result.ministerial_role is not None
            assert result.ministerial_role.title == "Minister of Finance"
            assert len(result.committees) == 1
            assert result.committees[0].name == "Finance"

    async def test_mp_not_found(self):
        """Test returns None when MP not found for riding."""
        with patch(
            "api.civic_context.services.houseofcommons.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = MagicMock()

            # Clear caches
            import api.civic_context.services.houseofcommons as hoc_module
            hoc_module._mp_cache = None
            hoc_module._mp_cache_expires_at = None
            hoc_module._ministers_cache = None
            hoc_module._ministers_cache_expires_at = None
            hoc_module._secretaries_cache = None
            hoc_module._secretaries_cache_expires_at = None

            async def get_response(url):
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()

                if url == "/Members/en/search/XML":
                    mock_response.text = """
                    <ArrayOfMemberOfParliament>
                        <MemberOfParliament>
                            <PersonId>12345</PersonId>
                            <ConstituencyName>Toronto Centre</ConstituencyName>
                            <ConstituencyProvinceTerritoryName>Ontario</ConstituencyProvinceTerritoryName>
                            <CaucusShortName>Liberal</CaucusShortName>
                        </MemberOfParliament>
                    </ArrayOfMemberOfParliament>
                    """
                else:
                    mock_response.text = "<Empty/>"

                return mock_response

            mock_client.get = AsyncMock(side_effect=get_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await get_house_of_commons_data("Nonexistent Riding")

            assert result is None

    async def test_api_failure_returns_none(self):
        """Test API failure returns None gracefully."""
        with patch(
            "api.civic_context.services.houseofcommons.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = MagicMock()

            # Clear caches
            import api.civic_context.services.houseofcommons as hoc_module
            hoc_module._mp_cache = None
            hoc_module._mp_cache_expires_at = None
            hoc_module._ministers_cache = None
            hoc_module._ministers_cache_expires_at = None
            hoc_module._secretaries_cache = None
            hoc_module._secretaries_cache_expires_at = None

            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await get_house_of_commons_data("Ottawa Centre")

            assert result is None

    async def test_constituency_matching_with_dashes(self):
        """Test constituency matching works with different dash types."""
        with patch(
            "api.civic_context.services.houseofcommons.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = MagicMock()

            # Clear caches
            import api.civic_context.services.houseofcommons as hoc_module
            hoc_module._mp_cache = None
            hoc_module._mp_cache_expires_at = None
            hoc_module._ministers_cache = None
            hoc_module._ministers_cache_expires_at = None
            hoc_module._secretaries_cache = None
            hoc_module._secretaries_cache_expires_at = None

            async def get_response(url):
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()

                if url == "/Members/en/search/XML":
                    # HOC uses em-dash
                    mock_response.text = """
                    <ArrayOfMemberOfParliament>
                        <MemberOfParliament>
                            <PersonId>12345</PersonId>
                            <ConstituencyName>Saint-Maurice—Champlain</ConstituencyName>
                            <ConstituencyProvinceTerritoryName>Quebec</ConstituencyProvinceTerritoryName>
                            <CaucusShortName>Liberal</CaucusShortName>
                        </MemberOfParliament>
                    </ArrayOfMemberOfParliament>
                    """
                elif url == "/Members/en/ministries/XML":
                    mock_response.text = "<ArrayOfCabinetMember></ArrayOfCabinetMember>"
                elif url == "/Members/en/parliamentary-secretaries/XML":
                    mock_response.text = "<ArrayOfParliamentarySecretary></ArrayOfParliamentarySecretary>"
                elif url == "/Members/en/12345/XML":
                    mock_response.text = "<MemberOfParliament><PersonId>12345</PersonId></MemberOfParliament>"
                else:
                    mock_response.text = "<Empty/>"

                return mock_response

            mock_client.get = AsyncMock(side_effect=get_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Search with regular hyphen (Represent API style)
            result = await get_house_of_commons_data("Saint-Maurice-Champlain")

            assert result is not None
            assert result.hoc_person_id == 12345
