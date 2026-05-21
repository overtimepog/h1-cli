"""Tests for h1cli API client."""

import pytest
import httpx
from pytest_httpx import HTTPXMock

from h1cli.client import H1Client, Program, BountyTable


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
