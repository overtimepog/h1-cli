"""Tests for h1cli API client."""

import pytest
import httpx
from pytest_httpx import HTTPXMock

from h1cli.client import H1Client, Program, BountyTable, SearchFilters, HacktivityItem


# ── fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return H1Client()


@pytest.fixture
def sample_graphql_response():
    return {
        "data": {
            "teams": {
                "edges": [{
                    "node": {
                        "handle": "security",
                        "name": "HackerOne",
                        "url": "https://hackerone.com/security",
                        "offers_bounties": True,
                        "minimum_bounty": 200,
                        "average_bounty_upper_amount": 500,
                        "average_bounty_lower_amount": 150,
                        "currency": "usd",
                        "resolved_report_count": 990,
                        "created_at": "2020-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "about": "HackerOne program",
                        "industry": "Technology",
                        "submission_state": "open",
                        "triage_active": True,
                        "bounty_time": 24.5,
                        "response_efficiency_percentage": 95,
                        "bounties_total": "10M+",
                        "structured_scopes": {
                            "edges": [
                                {"node": {
                                    "asset_identifier": "hackerone.com",
                                    "asset_type": "URL",
                                    "eligible_for_bounty": True,
                                    "eligible_for_submission": True,
                                }},
                                {"node": {
                                    "asset_identifier": "api.hackerone.com",
                                    "asset_type": "URL",
                                    "eligible_for_bounty": True,
                                    "eligible_for_submission": True,
                                }},
                            ]
                        },
                        "bounty_table": {
                            "bounty_table_rows": {
                                "edges": [
                                    {"node": {
                                        "name": "Critical",
                                        "critical": 5000,
                                        "critical_minimum": 2500,
                                        "high": 3000,
                                        "high_minimum": 1500,
                                        "medium": 1000,
                                        "medium_minimum": 500,
                                        "low": 250,
                                        "low_minimum": 200,
                                    }},
                                ]
                            }
                        },
                    }
                }]
            }
        }
    }


@pytest.fixture
def sample_search_response():
    return {
        "limit": 10,
        "total": 454,
        "results": [
            {
                "id": 70892,
                "url": "/anthropic",
                "name": "Anthropic",
                "handle": "anthropic",
                "meta": {
                    "submission_state": "open",
                    "resolved_report_count": 289,
                    "minimum_bounty": 50,
                    "default_currency": "usd",
                    "offers_bounties": True,
                    "quick_to_bounty": True,
                    "quick_to_first_response": True,
                    "triage_active": True,
                },
                "about": "Anthropic is an AI safety company.",
                "stripped_policy": "Policy text...",
                "profile_picture": "https://example.com/pic.jpg",
                "internet_bug_bounty": False,
                "team_type": "team",
            }
        ],
    }


@pytest.fixture
def multi_graphql_response():
    """Two programs for search result tests."""
    return {
        "data": {
            "teams": {
                "edges": [
                    {"node": {
                        "handle": "security",
                        "name": "HackerOne",
                        "url": "https://hackerone.com/security",
                        "offers_bounties": True,
                        "minimum_bounty": 200,
                        "average_bounty_upper_amount": 500,
                        "average_bounty_lower_amount": 150,
                        "currency": "usd",
                        "resolved_report_count": 990,
                        "submission_state": "open",
                        "triage_active": True,
                        "response_efficiency_percentage": 95,
                        "bounties_total": "10M+",
                        "about": "HackerOne program",
                        "industry": "Technology",
                        "structured_scopes": {
                            "edges": [
                                {"node": {
                                    "asset_identifier": "hackerone.com",
                                    "asset_type": "URL",
                                    "eligible_for_bounty": True,
                                    "eligible_for_submission": True,
                                }},
                            ]
                        },
                        "bounty_table": None,
                    }},
                    {"node": {
                        "handle": "anthropic",
                        "name": "Anthropic",
                        "url": "https://hackerone.com/anthropic",
                        "offers_bounties": True,
                        "minimum_bounty": 50,
                        "average_bounty_upper_amount": 1600,
                        "average_bounty_lower_amount": 1000,
                        "currency": "usd",
                        "resolved_report_count": 289,
                        "submission_state": "open",
                        "triage_active": True,
                        "response_efficiency_percentage": 98,
                        "bounties_total": "2M+",
                        "about": "AI safety company",
                        "industry": "Professional Services",
                        "structured_scopes": {
                            "edges": [
                                {"node": {
                                    "asset_identifier": "claude.ai",
                                    "asset_type": "URL",
                                    "eligible_for_bounty": True,
                                    "eligible_for_submission": True,
                                }},
                            ]
                        },
                        "bounty_table": None,
                    }},
                ]
            }
        }
    }


# ── Program dataclass ───────────────────────────────────────────────────

class TestProgram:
    def test_from_graphql_node(self, sample_graphql_response):
        node = sample_graphql_response["data"]["teams"]["edges"][0]["node"]
        program = Program.from_graphql(node)

        assert program.handle == "security"
        assert program.name == "HackerOne"
        assert program.url == "https://hackerone.com/security"
        assert program.offers_bounties is True
        assert program.minimum_bounty == 200
        assert program.average_bounty_upper == 500
        assert program.average_bounty_lower == 150
        assert program.currency == "usd"
        assert program.resolved_report_count == 990
        assert program.about == "HackerOne program"
        assert program.industry == "Technology"
        assert program.submission_state == "open"
        assert program.triage_active is True
        assert program.bounty_time_hours == 24.5
        assert program.response_efficiency == 95
        assert program.bounties_total == "10M+"
        assert len(program.scopes) == 2
        assert program.scopes[0]["asset_identifier"] == "hackerone.com"
        assert program.bounty_table is not None

    def test_from_graphql_minimal(self):
        node = {
            "handle": "testprog",
            "name": "Test Program",
            "url": "https://hackerone.com/testprog",
        }
        program = Program.from_graphql(node)
        assert program.handle == "testprog"
        assert program.name == "Test Program"
        assert program.offers_bounties is False
        assert program.minimum_bounty is None
        assert program.scopes == []

    def test_from_search_result(self, sample_search_response):
        result = sample_search_response["results"][0]
        program = Program.from_search(result)

        assert program.handle == "anthropic"
        assert program.name == "Anthropic"
        assert program.url == "https://hackerone.com/anthropic"
        assert program.minimum_bounty == 50
        assert program.offers_bounties is True
        assert program.resolved_report_count == 289
        assert program.about == "Anthropic is an AI safety company."

    def test_matches_filters_asset(self):
        """Program.matches_filters with asset filter."""
        p = Program(handle="test", name="Test")
        p.scopes = [
            {"asset_identifier": "*.google.com", "asset_type": "URL"},
            {"asset_identifier": "api.example.com", "asset_type": "URL"},
        ]
        # Asset filter matches any scope
        f = SearchFilters(asset="google.com")
        assert p.matches_filters(f) is True

        f2 = SearchFilters(asset="microsoft.com")
        assert p.matches_filters(f2) is False

    def test_matches_filters_paid(self):
        """Program.matches_filters with paid/unpaid filter."""
        p1 = Program(handle="paid", name="Paid", offers_bounties=True, minimum_bounty=100)
        p2 = Program(handle="vdp", name="VDP", offers_bounties=False)

        assert p1.matches_filters(SearchFilters(paid=True)) is True
        assert p2.matches_filters(SearchFilters(paid=True)) is False
        assert p1.matches_filters(SearchFilters(paid=False)) is False
        assert p2.matches_filters(SearchFilters(paid=False)) is True

    def test_matches_filters_min_bounty(self):
        """Program.matches_filters with min_bounty filter."""
        p = Program(handle="test", name="Test", offers_bounties=True, minimum_bounty=500)
        assert p.matches_filters(SearchFilters(min_bounty=100)) is True
        assert p.matches_filters(SearchFilters(min_bounty=500)) is True
        assert p.matches_filters(SearchFilters(min_bounty=1000)) is False
        # Program with no minimum_bounty
        p2 = Program(handle="none", name="None", offers_bounties=True, minimum_bounty=None)
        assert p2.matches_filters(SearchFilters(min_bounty=500)) is False

    def test_matches_filters_min_reports(self):
        """Program.matches_filters with min_reports filter."""
        p = Program(handle="test", name="Test", resolved_report_count=200)
        assert p.matches_filters(SearchFilters(min_reports=50)) is True
        assert p.matches_filters(SearchFilters(min_reports=200)) is True
        assert p.matches_filters(SearchFilters(min_reports=500)) is False

    def test_matches_filters_combined(self):
        """Program.matches_filters with multiple filters."""
        p = Program(handle="test", name="Test", offers_bounties=True,
                     minimum_bounty=500, resolved_report_count=200)
        p.scopes = [{"asset_identifier": "*.google.com", "asset_type": "URL"}]

        # All match
        f = SearchFilters(asset="google", paid=True, min_bounty=100, min_reports=50)
        assert p.matches_filters(f) is True

        # One mismatch
        f2 = SearchFilters(asset="google", paid=True, min_bounty=1000, min_reports=50)
        assert p.matches_filters(f2) is False

    def test_matches_filters_none(self):
        """Empty SearchFilters matches everything."""
        p = Program(handle="test", name="Test")
        assert p.matches_filters(SearchFilters()) is True


class TestBountyTable:
    def test_from_graphql(self, sample_graphql_response):
        node = sample_graphql_response["data"]["teams"]["edges"][0]["node"]
        bt = BountyTable.from_graphql(node.get("bounty_table"))

        assert bt is not None
        assert len(bt.rows) == 1
        row = bt.rows[0]
        assert row["name"] == "Critical"
        assert row["critical"] == 5000
        assert row["high"] == 3000
        assert row["medium"] == 1000
        assert row["low"] == 250

    def test_from_graphql_none(self):
        bt = BountyTable.from_graphql(None)
        assert bt is None


# ── H1Client GraphQL ────────────────────────────────────────────────────

class TestH1ClientGraphQL:
    def test_get_program_graphql(self, client, httpx_mock: HTTPXMock, sample_graphql_response):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=sample_graphql_response,
        )

        program = client.get_program("security")

        assert program is not None
        assert program.handle == "security"
        assert program.name == "HackerOne"

        # Verify the GraphQL query was sent
        request = httpx_mock.get_requests()[0]
        body = request.content.decode()
        assert "security" in body
        assert "query" in body

    def test_get_program_not_found(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json={"data": {"teams": {"edges": []}}},
        )

        program = client.get_program("nonexistent")
        assert program is None

    def test_get_program_http_error(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            status_code=500,
        )

        with pytest.raises(httpx.HTTPStatusError):
            client.get_program("test")


# ── H1Client search ─────────────────────────────────────────────────────

class TestH1ClientSearch:
    def test_search_programs(self, client, httpx_mock: HTTPXMock, sample_search_response):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true&sort=resolved_report_count:descending&limit=25",
            method="GET",
            json=sample_search_response,
        )

        programs, total = client.search_programs(
            sort="resolved_report_count:descending",
            limit=25,
        )

        assert total == 454
        assert len(programs) == 1
        assert programs[0].handle == "anthropic"

    def test_search_programs_defaults(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true&sort=resolved_report_count:descending&limit=25",
            method="GET",
            json={"limit": 0, "total": 0, "results": []},
        )

        programs, total = client.search_programs()
        assert total == 0

    def test_search_programs_no_results(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true+xyzznonexistent123&sort=resolved_report_count:descending&limit=25",
            method="GET",
            json={"limit": 0, "total": 0, "results": []},
        )

        programs, total = client.search_programs(query="xyzznonexistent123")
        assert total == 0
        assert programs == []

    def test_search_programs_with_keyword(self, client, httpx_mock: HTTPXMock, sample_search_response):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true+anthropic&sort=resolved_report_count:descending&limit=25",
            method="GET",
            json=sample_search_response,
        )

        programs, total = client.search_programs(query="anthropic")
        assert total == 454


# ── GraphQL search with structured filters ───────────────────────────────

class TestH1ClientGraphQLSearch:
    """Tests for search_programs_graphql with structured filters."""

    def test_search_all(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """Basic GraphQL search with no filters returns all programs."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(limit=25)

        assert len(programs) == 2
        assert programs[0].handle == "security"
        assert programs[1].handle == "anthropic"

        # Verify the query has no structured_scopes filter (just keyword in policy)
        request = httpx_mock.get_requests()[0]
        body = request.content.decode()
        assert "structured_scopes" not in body or "_ilike" not in body

    def test_search_by_asset(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """Search filtering by asset identifier."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            filters=SearchFilters(asset="claude.ai"),
        )

        # Both programs are returned from GraphQL, but client-side filtering
        # should reduce to only the one with matching asset
        assert len(programs) == 1
        assert programs[0].handle == "anthropic"

    def test_search_by_keyword(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """Search by keyword in policy text."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            keyword="safety",
        )
        assert len(programs) == 2  # Both have content

        # Verify keyword was in the query
        request = httpx_mock.get_requests()[0]
        body = request.content.decode()
        assert "safety" in body

    def test_search_paid_only(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """Search filtering paid programs only (via GraphQL where clause)."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            filters=SearchFilters(paid=True),
        )
        assert len(programs) == 2  # Both offer bounties

    def test_search_unpaid(self, client, httpx_mock: HTTPXMock):
        """Search for unpaid/VDP programs."""
        resp = {
            "data": {
                "teams": {
                    "edges": [
                        {"node": {
                            "handle": "vdp-prog",
                            "name": "VDP Program",
                            "url": "https://hackerone.com/vdp-prog",
                            "offers_bounties": False,
                            "minimum_bounty": None,
                            "resolved_report_count": 5,
                            "submission_state": "open",
                            "triage_active": False,
                            "structured_scopes": {"edges": []},
                            "bounty_table": None,
                        }},
                    ]
                }
            }
        }
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=resp,
        )

        programs = client.search_programs_graphql(
            filters=SearchFilters(paid=False),
        )
        assert len(programs) == 1
        assert programs[0].handle == "vdp-prog"

    def test_search_by_min_bounty_client_side(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """min_bounty is filtered client-side since GraphQL doesn't support it in where."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            filters=SearchFilters(min_bounty=200),
        )
        # Only HackerOne (min_bounty=200), not Anthropic (min_bounty=50)
        assert len(programs) == 1
        assert programs[0].handle == "security"

    def test_search_by_min_reports_client_side(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """min_reports is filtered client-side."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            filters=SearchFilters(min_reports=500),
        )
        # Only HackerOne (990 resolved), not Anthropic (289)
        assert len(programs) == 1
        assert programs[0].handle == "security"

    def test_search_combined_filters(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """Multiple filters combine correctly."""
        # First call: asset=claude.ai + min_bounty>=200 → zero results
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            filters=SearchFilters(asset="claude.ai", min_bounty=200),
        )
        assert len(programs) == 0  # Anthropic has min_bounty=50 < 200

        # Second call: asset=hackerone + min_reports>=500 → only HackerOne
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            filters=SearchFilters(asset="hackerone.com", min_reports=500),
        )
        assert len(programs) == 1
        assert programs[0].handle == "security"

    def test_search_sort_by_bounty(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """Sort results by minimum bounty descending."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            sort="minimum_bounty",
        )
        # HackerOne (200) > Anthropic (50)
        assert programs[0].handle == "security"

    def test_search_sort_by_reports(self, client, httpx_mock: HTTPXMock, multi_graphql_response):
        """Sort results by resolved report count."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=multi_graphql_response,
        )

        programs = client.search_programs_graphql(
            sort="resolved_report_count",
        )
        # HackerOne (990) > Anthropic (289)
        assert programs[0].handle == "security"

    def test_search_empty_results(self, client, httpx_mock: HTTPXMock):
        """Empty GraphQL response returns empty list."""
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json={"data": {"teams": {"edges": []}}},
        )

        programs = client.search_programs_graphql()
        assert programs == []


# ── Helpers ─────────────────────────────────────────────────────────────

class TestHelpers:
    def test_build_query_default(self):
        query = H1Client._build_search_query()
        assert "type:hackerone" in query
        assert "offers_bounties:true" in query

    def test_build_query_with_keyword(self):
        query = H1Client._build_search_query("google")
        assert "type:hackerone" in query
        assert "offers_bounties:true" in query
        assert "google" in query

    def test_build_query_custom(self):
        query = H1Client._build_search_query(
            "anthropic",
            filters={"submission_state": "open", "minimum_bounty": ">500"},
        )
        assert "type:hackerone" in query
        assert "anthropic" in query
        assert "minimum_bounty:>500" in query


# ── Hacktivity fixtures ─────────────────────────────────────────────────

@pytest.fixture
def sample_hacktivity_response():
    """GraphQL response for hacktivity_items query."""
    return {
        "data": {
            "hacktivity_items": {
                "edges": [
                    {
                        "node": {
                            "id": "h1:12345",
                            "report": {
                                "database_id": 12345,
                                "title": "SSRF via webhook leads to internal network access",
                                "url": "https://hackerone.com/reports/12345",
                                "severity_rating": "critical",
                                "bounty_amount": "15000",
                                "currency": "usd",
                                "disclosed_at": "2024-06-15T10:30:00Z",
                                "reporter": {
                                    "username": "alice_hacker",
                                    "profile_picture": "https://example.com/alice.jpg",
                                },
                            },
                            "team": {
                                "handle": "security",
                                "name": "HackerOne",
                                "url": "https://hackerone.com/security",
                            },
                        }
                    },
                    {
                        "node": {
                            "id": "h1:67890",
                            "report": {
                                "database_id": 67890,
                                "title": "XSS in comment field bypasses CSP",
                                "url": "https://hackerone.com/reports/67890",
                                "severity_rating": "high",
                                "bounty_amount": "2500",
                                "currency": "usd",
                                "disclosed_at": "2024-06-14T08:00:00Z",
                                "reporter": {
                                    "username": "bob_researcher",
                                    "profile_picture": "https://example.com/bob.jpg",
                                },
                            },
                            "team": {
                                "handle": "anthropic",
                                "name": "Anthropic",
                                "url": "https://hackerone.com/anthropic",
                            },
                        }
                    },
                ]
            }
        }
    }


@pytest.fixture
def hacktivity_empty_response():
    return {"data": {"hacktivity_items": {"edges": []}}}


# ── HacktivityItem ──────────────────────────────────────────────────────

class TestHacktivityItem:
    def test_from_graphql(self, sample_hacktivity_response):
        node = sample_hacktivity_response["data"]["hacktivity_items"]["edges"][0]["node"]
        item = HacktivityItem.from_graphql(node)

        assert item.report_id == 12345
        assert item.title == "SSRF via webhook leads to internal network access"
        assert item.severity == "critical"
        assert item.bounty_amount == "15000"
        assert item.currency == "usd"
        assert item.reporter_username == "alice_hacker"
        assert item.program_handle == "security"
        assert item.program_name == "HackerOne"

    def test_from_graphql_minimal(self):
        node = {
            "report": {
                "database_id": 1,
                "title": "Test",
                "url": "https://hackerone.com/reports/1",
                "severity_rating": "none",
                "bounty_amount": None,
                "currency": "usd",
                "disclosed_at": None,
                "reporter": {"username": "anon", "profile_picture": ""},
            },
            "team": {"handle": "test", "name": "Test Program", "url": "https://hackerone.com/test"},
        }
        item = HacktivityItem.from_graphql(node)
        assert item.report_id == 1
        assert item.severity == "none"
        assert item.bounty_amount is None
        assert item.disclosed_at is None


# ── H1Client get_hacktivity() ───────────────────────────────────────────

class TestH1ClientHacktivity:
    def test_get_hacktivity(self, client, httpx_mock: HTTPXMock, sample_hacktivity_response):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=sample_hacktivity_response,
        )

        items = client.get_hacktivity(limit=10)

        assert len(items) == 2
        assert items[0].title == "SSRF via webhook leads to internal network access"
        assert items[0].program_handle == "security"
        assert items[1].program_handle == "anthropic"

    def test_get_hacktivity_by_handle(self, client, httpx_mock: HTTPXMock, sample_hacktivity_response):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=sample_hacktivity_response,
        )

        items = client.get_hacktivity(limit=10, handle="anthropic")

        assert len(items) == 1
        assert items[0].program_handle == "anthropic"

    def test_get_hacktivity_empty(self, client, httpx_mock: HTTPXMock, hacktivity_empty_response):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=hacktivity_empty_response,
        )

        items = client.get_hacktivity()
        assert items == []

    def test_get_hacktivity_http_error(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            status_code=500,
        )

        with pytest.raises(httpx.HTTPStatusError):
            client.get_hacktivity()


# ── Program policy (stripped_policy) ────────────────────────────────────

class TestProgramPolicy:
    def test_stripped_policy_parsed(self, sample_graphql_response):
        """Verify stripped_policy is parsed from GraphQL response."""
        sample_graphql_response["data"]["teams"]["edges"][0]["node"]["stripped_policy"] = (
            "# Program Policy\n\nPlease report security bugs.\n\n## Scope\n\n"
            "* hackerone.com\n* api.hackerone.com\n\n## Out of Scope\n\n"
            "* social engineering\n* denial of service"
        )
        node = sample_graphql_response["data"]["teams"]["edges"][0]["node"]
        program = Program.from_graphql(node)

        assert program.stripped_policy != ""
        assert "security bugs" in program.stripped_policy
        assert "hackerone.com" in program.stripped_policy

    def test_stripped_policy_missing(self, sample_graphql_response):
        """Program with no stripped_policy field defaults to empty string."""
        node = sample_graphql_response["data"]["teams"]["edges"][0]["node"]
        program = Program.from_graphql(node)

        assert program.stripped_policy == ""
