"""HackerOne API client — GraphQL + REST search."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Any

import httpx


GRAPHQL_URL = "https://hackerone.com/graphql"
SEARCH_URL = "https://hackerone.com/programs/search.json"

USER_AGENT = "Mozilla/5.0 (compatible; h1cli/0.1; +https://github.com/overtimepog/h1cli)"

PROGRAM_QUERY = """
query($handle: String!) {
  teams(first: 1, where: {handle: {_eq: $handle}, submission_state: {_eq: open}}) {
    edges {
      node {
        handle
        name
        url
        offers_bounties
        minimum_bounty
        average_bounty_upper_amount
        average_bounty_lower_amount
        currency
        resolved_report_count
        created_at
        updated_at
        about
        industry
        submission_state
        triage_active
        bounty_time
        response_efficiency_percentage
        bounties_total
        top_bounty_upper_amount
        top_bounty_lower_amount
        profile_picture(size: medium)
        internet_bug_bounty
        structured_scopes(first: 200) {
          edges {
            node {
              asset_identifier
              asset_type
              eligible_for_bounty
              eligible_for_submission
            }
          }
        }
        bounty_table {
          bounty_table_rows(first: 50) {
            edges {
              node {
                name
                critical
                critical_minimum
                high
                high_minimum
                medium
                medium_minimum
                low
                low_minimum
                description
              }
            }
          }
        }
      }
    }
  }
}
"""


@dataclass
class BountyTable:
    """Represents a program's bounty table with severity → amount mappings."""

    rows: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_graphql(cls, data: dict | None) -> BountyTable | None:
        if not data:
            return None
        rows_data = data.get("bounty_table_rows", {}).get("edges", [])
        if not rows_data:
            return None
        rows = [e["node"] for e in rows_data]
        return cls(rows=rows)


@dataclass
class Program:
    """Represents a HackerOne bug bounty program."""

    handle: str
    name: str
    url: str = ""
    offers_bounties: bool = False
    minimum_bounty: int | None = None
    average_bounty_upper: int | None = None
    average_bounty_lower: int | None = None
    currency: str = "usd"
    resolved_report_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    about: str = ""
    industry: str = ""
    submission_state: str = ""
    triage_active: bool = False
    bounty_time_hours: float | None = None
    response_efficiency: int | None = None
    bounties_total: str = ""
    top_bounty_upper: int | None = None
    top_bounty_lower: int | None = None
    profile_picture: str = ""
    internet_bug_bounty: bool = False
    scopes: list[dict[str, Any]] = field(default_factory=list)
    bounty_table: BountyTable | None = None

    @classmethod
    def from_graphql(cls, node: dict) -> Program:
        """Create a Program from a GraphQL team node."""
        scopes_data = node.get("structured_scopes", {}).get("edges", [])
        scopes = [e["node"] for e in scopes_data]

        return cls(
            handle=node.get("handle", ""),
            name=node.get("name", ""),
            url=node.get("url", f"https://hackerone.com/{node.get('handle', '')}"),
            offers_bounties=node.get("offers_bounties") or False,
            minimum_bounty=node.get("minimum_bounty"),
            average_bounty_upper=node.get("average_bounty_upper_amount"),
            average_bounty_lower=node.get("average_bounty_lower_amount"),
            currency=node.get("currency", "usd"),
            resolved_report_count=node.get("resolved_report_count", 0),
            created_at=node.get("created_at"),
            updated_at=node.get("updated_at"),
            about=node.get("about", ""),
            industry=node.get("industry", ""),
            submission_state=node.get("submission_state", ""),
            triage_active=node.get("triage_active", False),
            bounty_time_hours=node.get("bounty_time"),
            response_efficiency=node.get("response_efficiency_percentage"),
            bounties_total=node.get("bounties_total", ""),
            top_bounty_upper=node.get("top_bounty_upper_amount"),
            top_bounty_lower=node.get("top_bounty_lower_amount"),
            profile_picture=node.get("profile_picture", ""),
            internet_bug_bounty=node.get("internet_bug_bounty", False),
            scopes=scopes,
            bounty_table=BountyTable.from_graphql(node.get("bounty_table")),
        )

    @classmethod
    def from_search(cls, result: dict) -> Program:
        """Create a Program from a REST search result."""
        meta = result.get("meta", {})
        return cls(
            handle=result.get("handle", ""),
            name=result.get("name", ""),
            url=f"https://hackerone.com{result.get('url', '')}",
            offers_bounties=meta.get("offers_bounties") or False,
            minimum_bounty=meta.get("minimum_bounty"),
            currency=meta.get("default_currency", "usd"),
            resolved_report_count=meta.get("resolved_report_count", 0),
            about=result.get("about", ""),
            submission_state=meta.get("submission_state", ""),
            triage_active=meta.get("triage_active", False),
            profile_picture=result.get("profile_picture", ""),
        )


class H1Client:
    """Async HTTP client for HackerOne's public API."""

    def __init__(self, timeout: float = 30.0):
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── GraphQL ──────────────────────────────────────────────────────

    def get_program(self, handle: str) -> Program | None:
        """Fetch a single program by handle via GraphQL."""
        resp = self._client.post(
            GRAPHQL_URL,
            json={
                "query": PROGRAM_QUERY,
                "variables": {"handle": handle},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        edges = data.get("data", {}).get("teams", {}).get("edges", [])
        if not edges:
            return None
        return Program.from_graphql(edges[0]["node"])

    # ── REST search ──────────────────────────────────────────────────

    @staticmethod
    def _build_search_query(
        keyword: str = "",
        filters: dict[str, str] | None = None,
    ) -> str:
        """Build a HackerOne search query string."""
        parts = ["type:hackerone", "offers_bounties:true"]
        if filters:
            for k, v in filters.items():
                parts.append(f"{k}:{v}")
        if keyword:
            parts.append(keyword)
        return " ".join(parts)

    def search_programs(
        self,
        query: str = "",
        sort: str = "resolved_report_count:descending",
        limit: int = 25,
        filters: dict[str, str] | None = None,
    ) -> tuple[list[Program], int]:
        """Search programs via the REST search API."""
        search_query = self._build_search_query(query, filters)
        # HackerOne's REST API uses + for spaces and literal : in query params
        params = {
            "query": search_query,
            "sort": sort,
            "limit": str(limit),
        }
        # Build URL manually — urlencode would encode : as %3A which breaks the API
        query_string = "&".join(
            f"{k}={urllib.parse.quote(v, safe=':+')}" for k, v in params.items()
        )
        url = f"{SEARCH_URL}?{query_string}"
        resp = self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        programs = [Program.from_search(r) for r in data.get("results", [])]
        total = data.get("total", 0)
        return programs, total
