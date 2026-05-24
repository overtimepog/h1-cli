"""HackerOne API client — GraphQL + REST search."""

from __future__ import annotations

import urllib.parse
import json
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
        policy
        structured_scopes(first: 50) {
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

# GraphQL search query — uses structured filters where supported,
# falls back to client-side filtering for bounty/report counts.
SEARCH_GQL_QUERY = """
query($first: Int!, $where: FiltersTeamFilterInput!) {
  teams(first: $first, where: $where) {
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
        structured_scopes(first: 50) {
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
class SearchFilters:
    """Structured search filters for GraphQL-based program search.

    Fields that map to GraphQL where clauses:
        keyword: text search in policy (searchable_content.policy._ilike)
        asset: filter by asset_identifier in scope (structured_scopes.asset_identifier._ilike)
        paid: offers_bounties (True = paid programs, False = VDP only, None = both)
        submission_state: 'open' (default) or 'closed'

    Fields filtered client-side (not in GraphQL where):
        min_bounty: minimum minimum_bounty (USD)
        min_reports: minimum resolved_report_count
    """

    keyword: str = ""
    asset: str = ""
    paid: bool | None = None
    submission_state: str = "open"
    min_bounty: int | None = None
    min_reports: int | None = None

    def build_graphql_where(self) -> dict:
        """Build the 'where' clause for the GraphQL teams query."""
        conditions = []

        # submission_state filter
        if self.submission_state:
            conditions.append({"submission_state": {"_eq": self.submission_state}})

        # paid/unpaid filter
        if self.paid is not None:
            conditions.append({"offers_bounties": {"_eq": self.paid}})

        # asset filter — match any scope containing the string
        if self.asset:
            conditions.append({
                "structured_scopes": {
                    "asset_identifier": {"_ilike": f"%{self.asset}%"}
                }
            })

        # keyword search in policy text
        if self.keyword:
            conditions.append({
                "searchable_content": {
                    "policy": {"_ilike": f"%{self.keyword}%"}
                }
            })

        if not conditions:
            # Default: open programs
            return {"submission_state": {"_eq": "open"}}

        if len(conditions) == 1:
            return conditions[0]

        return {"_and": conditions}


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
    policy: str = ""

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
            resolved_report_count=node.get("resolved_report_count") or 0,
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
            policy=node.get("policy", ""),
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

    def matches_filters(self, filters: SearchFilters) -> bool:
        """Check if this program matches client-side filters.

        Checks all filter fields even though asset/paid/keyword are also
        handled server-side by GraphQL — this provides defense-in-depth.
        """
        # Paid/unpaid
        if filters.paid is not None:
            if bool(self.offers_bounties) != filters.paid:
                return False
        # Asset — match against any scope's asset_identifier
        if filters.asset:
            asset_lower = filters.asset.lower()
            if not any(
                asset_lower in s.get("asset_identifier", "").lower()
                for s in (self.scopes or [])
            ):
                return False
        # Min bounty
        if filters.min_bounty is not None:
            if self.minimum_bounty is None or self.minimum_bounty < filters.min_bounty:
                return False
        # Min resolved reports
        if filters.min_reports is not None:
            if (self.resolved_report_count or 0) < filters.min_reports:
                return False
        return True


# GraphQL hacktivity query — publicly disclosed reports
HACKTIVITY_QUERY = """
query($first: Int!, $handle: String, $severity: SeverityRatingEnum) {
  hacktivity_items(
    first: $first,
    where: {
      report: { disclosed_at: { _is_null: false } }
    },
    order_by: { field: popular, direction: DESC }
  ) {
    edges {
      node {
        id
        report {
          database_id: _id
          title
          url
          severity_rating
          bounty_amount
          currency
          disclosed_at
          reporter {
            username
            profile_picture(size: small)
          }
        }
        team {
          handle
          name
          url
        }
      }
    }
  }
}
"""


@dataclass
class HacktivityItem:
    """A publicly disclosed report on HackerOne's hacktivity feed."""

    report_id: int
    title: str
    url: str
    severity: str
    bounty_amount: str | None
    currency: str
    disclosed_at: str | None
    reporter_username: str
    reporter_picture: str
    program_handle: str
    program_name: str

    @classmethod
    def from_graphql(cls, node: dict) -> HacktivityItem:
        report = node.get("report", {})
        team = node.get("team", {})
        return cls(
            report_id=report.get("database_id", 0),
            title=report.get("title", ""),
            url=report.get("url", ""),
            severity=report.get("severity_rating", "none"),
            bounty_amount=report.get("bounty_amount"),
            currency=report.get("currency", "usd"),
            disclosed_at=report.get("disclosed_at"),
            reporter_username=report.get("reporter", {}).get("username", "anonymous"),
            reporter_picture=report.get("reporter", {}).get("profile_picture", ""),
            program_handle=team.get("handle", ""),
            program_name=team.get("name", ""),
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

    # ── GraphQL single program ────────────────────────────────────────

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

    # ── GraphQL search with structured filters ────────────────────────

    def search_programs_graphql(
        self,
        keyword: str = "",
        filters: SearchFilters | None = None,
        sort: str = "resolved_report_count",
        limit: int = 25,
    ) -> list[Program]:
        """Search programs via GraphQL with structured filters.

        Args:
            keyword: Text search in program policy content.
            filters: Structured filters (paid, asset, min_bounty, min_reports, etc.).
            sort: Sort field — 'resolved_report_count', 'minimum_bounty',
                  'response_efficiency_percentage', 'bounty_time'.
            limit: Max results to return.

        Returns:
            Filtered and sorted list of programs.
        """
        if filters is None:
            filters = SearchFilters()

        # Merge explicit keyword into filters if provided
        if keyword and not filters.keyword:
            filters.keyword = keyword

        where = filters.build_graphql_where()

        resp = self._client.post(
            GRAPHQL_URL,
            json={
                "query": SEARCH_GQL_QUERY,
                "variables": {
                    "first": min(limit * 3, 200),  # Fetch more to allow client-side filtering
                    "where": where,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        edges = data.get("data", {}).get("teams", {}).get("edges", [])
        programs = [Program.from_graphql(e["node"]) for e in edges]

        # Client-side filtering for fields not in GraphQL where clause
        # and defense-in-depth for asset/paid
        programs = [p for p in programs if p.matches_filters(filters)]

        # Sort (client-side for fields GraphQL doesn't sort)
        reverse = True
        key_map = {
            "resolved_report_count": lambda p: p.resolved_report_count or 0,
            "minimum_bounty": lambda p: p.minimum_bounty or 0,
            "response_efficiency_percentage": lambda p: p.response_efficiency or 0,
            "bounty_time": lambda p: -(p.bounty_time_hours or 99999),  # lower is better
        }
        key_fn = key_map.get(sort, key_map["resolved_report_count"])
        programs.sort(key=key_fn, reverse=reverse)

        return programs[:limit]

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
        """Search programs via the REST search API.

        Prefer search_programs_graphql() for structured filtering.
        This method is best for simple keyword searches.
        """
        search_query = self._build_search_query(query, filters)
        params = {
            "query": search_query,
            "sort": sort,
            "limit": str(limit),
        }
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

    # ── Hacktivity ───────────────────────────────────────────────────

    def get_hacktivity(
        self,
        limit: int = 25,
        handle: str | None = None,
    ) -> list[HacktivityItem]:
        """Fetch publicly disclosed reports from HackerOne's hacktivity feed.

        Args:
            limit: Max results (default 25).
            handle: Optional program handle to filter by.

        Returns:
            List of HacktivityItem objects sorted by popularity.
        """
        variables: dict[str, Any] = {"first": limit}
        if handle:
            variables["handle"] = handle

        resp = self._client.post(
            GRAPHQL_URL,
            json={
                "query": HACKTIVITY_QUERY,
                "variables": variables,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        edges = data.get("data", {}).get("hacktivity_items", {}).get("edges", [])
        items = [HacktivityItem.from_graphql(e["node"]) for e in edges]

        # Client-side filter by program handle if specified
        # (GraphQL where clause on team.handle may not always work)
        if handle:
            items = [
                i for i in items
                if i.program_handle.lower() == handle.lower()
            ]

        return items
