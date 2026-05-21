"""Tests for h1cli CLI commands."""

import pytest
from click.testing import CliRunner
from pytest_httpx import HTTPXMock

from h1cli.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def graphql_program_response():
    return {
        "data": {
            "teams": {
                "edges": [{
                    "node": {
                        "handle": "anthropic",
                        "name": "Anthropic",
                        "url": "https://hackerone.com/anthropic",
                        "offers_bounties": True,
                        "minimum_bounty": 50,
                        "average_bounty_upper_amount": 5000,
                        "average_bounty_lower_amount": 500,
                        "currency": "usd",
                        "resolved_report_count": 289,
                        "created_at": "2023-01-01T00:00:00Z",
                        "updated_at": "2024-06-01T00:00:00Z",
                        "about": "Anthropic is an AI safety company.",
                        "industry": "Technology",
                        "submission_state": "open",
                        "triage_active": True,
                        "bounty_time": 12.0,
                        "response_efficiency_percentage": 98,
                        "bounties_total": "2M+",
                        "structured_scopes": {
                            "edges": [
                                {"node": {
                                    "asset_identifier": "*.anthropic.com",
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
                                        "critical": 15000,
                                        "critical_minimum": 5000,
                                        "high": 10000,
                                        "high_minimum": 3000,
                                        "medium": 5000,
                                        "medium_minimum": 1500,
                                        "low": 1000,
                                        "low_minimum": 500,
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
def search_response():
    return {
        "limit": 25,
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
                "about": "AI safety company.",
                "stripped_policy": "...",
                "profile_picture": "",
                "internet_bug_bounty": False,
                "team_type": "team",
            },
            {
                "id": 440,
                "url": "/coinmate",
                "name": "CoinMate.io",
                "handle": "coinmate",
                "meta": {
                    "submission_state": "open",
                    "resolved_report_count": 64,
                    "minimum_bounty": 50,
                    "default_currency": "usd",
                    "offers_bounties": True,
                    "quick_to_bounty": True,
                    "quick_to_first_response": True,
                },
                "about": "Crypto trading platform.",
                "stripped_policy": "...",
                "profile_picture": "",
                "internet_bug_bounty": False,
                "team_type": "team",
            },
        ],
    }


# ── info command ────────────────────────────────────────────────────────

class TestInfoCommand:
    def test_info_by_handle(self, runner, httpx_mock: HTTPXMock, graphql_program_response):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=graphql_program_response,
        )

        result = runner.invoke(main, ["info", "anthropic"])
        assert result.exit_code == 0
        assert "Anthropic" in result.output
        assert "AI safety" in result.output
        assert "289" in result.output  # resolved count
        assert "$50" in result.output  # min bounty

    def test_info_not_found(self, runner, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json={"data": {"teams": {"edges": []}}},
        )

        result = runner.invoke(main, ["info", "nonexistent999"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_info_with_bounties(self, runner, httpx_mock: HTTPXMock, graphql_program_response):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=graphql_program_response,
        )

        result = runner.invoke(main, ["info", "anthropic", "--bounties"])
        assert result.exit_code == 0
        assert "Bounty Table" in result.output
        assert "Critical" in result.output
        assert "15000" in result.output or "$15,000" in result.output

    def test_info_with_scope(self, runner, httpx_mock: HTTPXMock, graphql_program_response):
        httpx_mock.add_response(
            url="https://hackerone.com/graphql",
            method="POST",
            json=graphql_program_response,
        )

        result = runner.invoke(main, ["info", "anthropic", "--scope"])
        assert result.exit_code == 0
        assert "anthropic.com" in result.output


# ── search command ──────────────────────────────────────────────────────

class TestSearchCommand:
    def test_search_default(self, runner, httpx_mock: HTTPXMock, search_response):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true&sort=resolved_report_count:descending&limit=25",
            method="GET",
            json=search_response,
        )

        result = runner.invoke(main, ["search"])
        assert result.exit_code == 0
        assert "454" in result.output  # total
        assert "Anthropic" in result.output
        assert "CoinMate" in result.output

    def test_search_with_keyword(self, runner, httpx_mock: HTTPXMock, search_response):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true+android&sort=resolved_report_count:descending&limit=25",
            method="GET",
            json=search_response,
        )

        result = runner.invoke(main, ["search", "android"])
        assert result.exit_code == 0

    def test_search_with_sort(self, runner, httpx_mock: HTTPXMock, search_response):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true&sort=minimum_bounty:descending&limit=25",
            method="GET",
            json=search_response,
        )

        result = runner.invoke(main, ["search", "--sort", "minimum_bounty:descending"])
        assert result.exit_code == 0

    def test_search_with_limit(self, runner, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true&sort=resolved_report_count:descending&limit=10",
            method="GET",
            json={"limit": 10, "total": 0, "results": []},
        )

        result = runner.invoke(main, ["search", "--limit", "10"])
        assert result.exit_code == 0

    def test_search_json_output(self, runner, httpx_mock: HTTPXMock, search_response):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true&sort=resolved_report_count:descending&limit=25",
            method="GET",
            json=search_response,
        )

        result = runner.invoke(main, ["search", "--json"])
        assert result.exit_code == 0
        # Should be valid JSON
        import json
        data = json.loads(result.output)
        assert "total" in data or isinstance(data, list)

    def test_search_no_results(self, runner, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true+zzzxxx&sort=resolved_report_count:descending&limit=25",
            method="GET",
            json={"limit": 0, "total": 0, "results": []},
        )

        result = runner.invoke(main, ["search", "zzzxxx"])
        assert result.exit_code == 0
        assert "0" in result.output or "no" in result.output.lower()


# ── top command ─────────────────────────────────────────────────────────

class TestTopCommand:
    def test_top_bounties(self, runner, httpx_mock: HTTPXMock, search_response):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true&sort=minimum_bounty:descending&limit=10",
            method="GET",
            json=search_response,
        )

        result = runner.invoke(main, ["top", "--bounties"])
        assert result.exit_code == 0

    def test_top_resolved(self, runner, httpx_mock: HTTPXMock, search_response):
        httpx_mock.add_response(
            url="https://hackerone.com/programs/search.json?query=type:hackerone+offers_bounties:true&sort=resolved_report_count:descending&limit=10",
            method="GET",
            json=search_response,
        )

        result = runner.invoke(main, ["top"])
        assert result.exit_code == 0


# ── main / help ─────────────────────────────────────────────────────────

class TestMainHelp:
    def test_no_args_shows_help(self, runner):
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Usage" in result.output or "Commands" in result.output

    def test_help_flag(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "search" in result.output
        assert "info" in result.output
        assert "top" in result.output
