"""HackerOne bounty CLI — search, browse, and analyze bug bounty programs."""

from __future__ import annotations

import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from .client import H1Client, Program, SearchFilters, HacktivityItem


console = Console()
error_console = Console(stderr=True)


def _fmt_money(amount: int | None, currency: str = "usd") -> str:
    """Format a currency amount nicely."""
    if amount is None:
        return "—"
    currency_map = {"usd": "$", "eur": "€", "gbp": "£", "chf": "CHF "}
    symbol = currency_map.get(currency.lower(), f"{currency.upper()} ")
    if amount >= 1_000_000:
        return f"{symbol}{amount / 1_000_000:.1f}M"
    if amount >= 1000:
        return f"{symbol}{amount:,}"
    return f"{symbol}{amount}"


def _fmt_bool(val: bool | None) -> str:
    if val is True:
        return "[green]✓[/green]"
    if val is False:
        return "[red]✗[/red]"
    return "—"


def _fmt_time_ago(iso_string: str | None) -> str:
    """Format an ISO timestamp as relative time."""
    if not iso_string:
        return "—"
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        if delta.days > 365:
            return f"{delta.days // 365}y ago"
        if delta.days > 30:
            return f"{delta.days // 30}mo ago"
        if delta.days > 0:
            return f"{delta.days}d ago"
        if delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        return f"{delta.seconds // 60}m ago"
    except Exception:
        return iso_string[:10]


def _fmt_severity(severity: str) -> str:
    """Format a severity rating with color."""
    colors = {
        "critical": "[bold red]CRITICAL[/bold red]",
        "high": "[red]HIGH[/red]",
        "medium": "[yellow]MEDIUM[/yellow]",
        "low": "[green]LOW[/green]",
        "none": "[dim]NONE[/dim]",
    }
    return colors.get(severity.lower() if severity else "none", severity.upper())


# ── CLI ──────────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.version_option(version="0.2.0", prog_name="h1")
@click.pass_context
def main(ctx):
    """h1 — HackerOne bounty program explorer for the terminal.

    Search, browse, and analyze bug bounty programs from HackerOne.
    No API key required — uses HackerOne's public API.

    \b
    Examples:
      h1 search android          Search for Android-related programs
      h1 info anthropic          Show detailed info on Anthropic's program
      h1 info anthropic -b       Show bounty table for Anthropic
      h1 top --bounties          Top programs by max bounty
      h1 hacktivity              Browse publicly disclosed reports
      h1 hacktivity -p anthropic Anthropic's disclosed reports
      h1 info anthropic -g       Show Anthropic's security guidelines
      h1 search google --json    JSON output for scripting
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("keyword", required=False, default="")
@click.option("--paid/--no-pay", "paid", default=None,
              help="Filter: paid bounty programs vs VDPs (no bounty)")
@click.option("--asset", "-a", default=None,
              help="Filter by asset in scope (e.g. 'google.com', '*.aws.amazon.com')")
@click.option("--min-bounty", "-mb", default=None, type=int,
              help="Minimum bounty amount in USD (e.g. 500)")
@click.option("--min-reports", "-mr", default=None, type=int,
              help="Minimum resolved reports (e.g. 100)")
@click.option("--sort-by", "-s",
              type=click.Choice(["reports", "bounty", "response"]),
              default="reports",
              help="Sort results by (default: reports)")
@click.option("--limit", "-n", default=25, type=int,
              help="Number of results (default: 25)")
@click.option("--json", "output_json", is_flag=True,
              help="Output as JSON")
@click.option("--fast", is_flag=True,
              help="Use REST search (faster, fewer filter options)")
def search(keyword: str, paid: bool | None, asset: str | None,
           min_bounty: int | None, min_reports: int | None,
           sort_by: str, limit: int, output_json: bool, fast: bool):
    """Search HackerOne bounty programs with powerful filters.

    \b
    KEYWORD: optional search term (matches in program name/policy).

    \b
    Examples:
      h1 search android --paid               Paid Android programs
      h1 search --asset=google.com            Programs with google.com in scope
      h1 search --min-bounty=500 --paid       Paid programs with $500+ minimum
      h1 search --min-reports=100             Established programs (100+ resolved)
      h1 search --no-pay --asset=example.com  VDPs with example.com in scope
      h1 search --fast google                 Quick REST search (keyword only)
    """
    sort_map = {
        "reports": "resolved_report_count",
        "bounty": "minimum_bounty",
        "response": "response_efficiency_percentage",
    }
    gql_sort = sort_map.get(sort_by, "resolved_report_count")

    with H1Client() as client:
        try:
            if fast and not any([paid is not None, asset, min_bounty, min_reports]):
                # Use REST for simple keyword searches
                programs, total = client.search_programs(
                    query=keyword, limit=limit,
                )
            else:
                # Use GraphQL with structured filters
                filters = SearchFilters(
                    keyword=keyword,
                    asset=asset or "",
                    paid=paid,
                    min_bounty=min_bounty,
                    min_reports=min_reports,
                )
                programs = client.search_programs_graphql(
                    keyword=keyword,
                    filters=filters,
                    sort=gql_sort,
                    limit=limit,
                )
                total = len(programs)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    if output_json:
        print(json.dumps(
            {"total": total, "results": [
                {
                    "handle": p.handle,
                    "name": p.name,
                    "url": p.url,
                    "offers_bounties": p.offers_bounties,
                    "minimum_bounty": p.minimum_bounty,
                    "currency": p.currency,
                    "resolved_report_count": p.resolved_report_count,
                    "triage_active": p.triage_active,
                    "about": p.about,
                    "scopes_count": len(p.scopes),
                }
                for p in programs
            ]},
            indent=2,
        ))
        return

    if not programs:
        console.print(f"[yellow]No programs found[/yellow] ({total} total)")
        return

    # Build active filters indicator
    active_filters = []
    if paid is True:
        active_filters.append("paid")
    elif paid is False:
        active_filters.append("VDP")
    if asset:
        active_filters.append(f"asset={asset}")
    if min_bounty:
        active_filters.append(f"min ${min_bounty}")
    if min_reports:
        active_filters.append(f"{min_reports}+ reports")
    filter_str = f" [{', '.join(active_filters)}]" if active_filters else ""

    table = Table(
        title=f"HackerOne Programs ({total} total, showing {len(programs)}){filter_str}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Program", style="bold")
    table.add_column("Min Bounty", justify="right")
    table.add_column("Avg Bounty", justify="right")
    table.add_column("Resolved", justify="right")
    table.add_column("Triage", justify="center", width=6)

    for i, p in enumerate(programs, 1):
        min_b = _fmt_money(p.minimum_bounty, p.currency)
        avg_b = _fmt_money(p.average_bounty_upper, p.currency)
        table.add_row(
            str(i),
            f"[link={p.url}]{p.name}[/link]\n[dim]{p.handle}[/dim]",
            min_b,
            avg_b,
            str(p.resolved_report_count),
            _fmt_bool(p.triage_active),
        )

    console.print(table)


@main.command()
@click.argument("handle")
@click.option("--bounties", "-b", is_flag=True,
              help="Show bounty table (severity → payout)")
@click.option("--scope", "-s", is_flag=True,
              help="Show in-scope assets")
@click.option("--guidelines", "-g", is_flag=True,
              help="Show program policy / guidelines")
@click.option("--json", "output_json", is_flag=True,
              help="Output as JSON")
def info(handle: str, bounties: bool, scope: bool, guidelines: bool, output_json: bool):
    """Show detailed info about a program by handle.

    Without flags, shows ALL sections (stats, bounties, scope, guidelines).
    With flags, only the requested sections are shown.

    HANDLE is the program slug (e.g. 'anthropic', 'security', 'vercel').
    """
    with H1Client() as client:
        try:
            program = client.get_program(handle)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    if program is None:
        error_console.print(f"[red]Program '{handle}' not found.[/red]")
        sys.exit(1)

    # Determine which sections to show
    any_section = bounties or scope or guidelines
    show_all = not any_section
    show_stats = show_all
    show_bounties = bounties or show_all
    show_scope = scope or show_all
    show_guidelines = guidelines or show_all

    if output_json:
        print(json.dumps({
            "handle": program.handle,
            "name": program.name,
            "url": program.url,
            "offers_bounties": program.offers_bounties,
            "minimum_bounty": program.minimum_bounty,
            "average_bounty_upper": program.average_bounty_upper,
            "average_bounty_lower": program.average_bounty_lower,
            "currency": program.currency,
            "resolved_report_count": program.resolved_report_count,
            "triage_active": program.triage_active,
            "bounty_time_hours": program.bounty_time_hours,
            "response_efficiency": program.response_efficiency,
            "bounties_total": program.bounties_total,
            "about": program.about,
            "industry": program.industry,
            "scopes": program.scopes,
            "bounty_table": program.bounty_table.rows if program.bounty_table else None,
            "policy": program.policy or "",
        }, indent=2))
        return

    # ── Header (always shown) ─────────────────────────────────────────
    header = Text()
    header.append(f"{program.name}", style="bold cyan")
    header.append(f"\n{program.url}", style="dim link={program.url}")
    if program.about:
        header.append(f"\n\n{program.about}", style="italic")
    console.print(Panel(header, title=f"[bold]{program.handle}[/bold]", border_style="cyan"))

    # ── Stats (shown when no section flags) ───────────────────────────
    if show_stats:
        stats = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        stats.add_column(style="dim")
        stats.add_column()

        state_color = "green" if program.submission_state == "open" else "yellow"
        stats.add_row("State", f"[{state_color}]{program.submission_state}[/{state_color}]")
        stats.add_row("Offers Bounties", _fmt_bool(program.offers_bounties))
        if program.minimum_bounty:
            stats.add_row("Minimum Bounty", _fmt_money(program.minimum_bounty, program.currency))
        if program.average_bounty_upper:
            avg = _fmt_money(program.average_bounty_upper, program.currency)
            if program.average_bounty_lower:
                avg = f"{_fmt_money(program.average_bounty_lower, program.currency)} – {_fmt_money(program.average_bounty_upper, program.currency)}"
            stats.add_row("Average Bounty", avg)
        if program.top_bounty_upper:
            top = _fmt_money(program.top_bounty_upper, program.currency)
            stats.add_row("Top Bounty", f"[yellow]{top}[/yellow]")
        stats.add_row("Resolved Reports", str(program.resolved_report_count))
        if program.bounties_total:
            stats.add_row("Total Paid", f"[green]{program.bounties_total}[/green]")
        stats.add_row("Triage Active", _fmt_bool(program.triage_active))
        if program.bounty_time_hours is not None:
            stats.add_row("Avg Time to Bounty", f"{program.bounty_time_hours:.0f}h")
        if program.response_efficiency is not None:
            stats.add_row("Response Efficiency", f"{program.response_efficiency}%")
        if program.industry:
            stats.add_row("Industry", program.industry)
        if program.updated_at:
            stats.add_row("Updated", _fmt_time_ago(program.updated_at))

        console.print(stats)

    # ── Bounty table ─────────────────────────────────────────────────
    if show_bounties and program.bounty_table:
        bt = program.bounty_table
        bt_table = Table(
            title="Bounty Table (USD)",
            box=box.ROUNDED,
            header_style="bold yellow",
        )
        bt_table.add_column("Severity", style="bold")
        bt_table.add_column("Min", justify="right")
        bt_table.add_column("Max", justify="right")

        for row in bt.rows:
            severities = {
                "critical": ("critical_minimum", "critical"),
                "high": ("high_minimum", "high"),
                "medium": ("medium_minimum", "medium"),
                "low": ("low_minimum", "low"),
            }
            has_severities = any(row.get(sev[0]) is not None or row.get(sev[1]) is not None
                                 for sev in severities.values())
            if has_severities:
                for sev_name, (min_key, max_key) in severities.items():
                    min_val = row.get(min_key)
                    max_val = row.get(max_key)
                    if min_val is not None or max_val is not None:
                        bt_table.add_row(
                            f"  {sev_name.title()}",
                            _fmt_money(min_val),
                            _fmt_money(max_val),
                        )
            else:
                bt_table.add_row(row.get("name", "—"), "—", "—")

        console.print(bt_table)

    # ── Scope ────────────────────────────────────────────────────────
    if show_scope and program.scopes:
        scope_table = Table(
            title="In-Scope Assets",
            box=box.ROUNDED,
            header_style="bold green",
        )
        scope_table.add_column("Asset", style="bold")
        scope_table.add_column("Type")
        scope_table.add_column("Bounty", justify="center")
        scope_table.add_column("Submission", justify="center")

        for s in program.scopes[:50]:
            scope_table.add_row(
                s.get("asset_identifier", "—"),
                s.get("asset_type", "—"),
                _fmt_bool(s.get("eligible_for_bounty")),
                _fmt_bool(s.get("eligible_for_submission")),
            )

        if len(program.scopes) > 50:
            scope_table.caption = f"... and {len(program.scopes) - 50} more assets"
        console.print(scope_table)

    # ── Guidelines / Policy ──────────────────────────────────────────
    if show_guidelines:
        if program.policy:
            console.print(Panel(
                program.policy,
                title="[bold cyan]Guidelines[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            ))
        else:
            console.print(
                f"[yellow]No policy text available for {program.name}.[/yellow]\n"
                f"[dim]Visit {program.url} to view the policy.[/dim]"
            )


@main.command()
@click.option("--bounties", "-b", "sort_by_bounty", is_flag=True,
              help="Sort by minimum bounty (highest first)")
@click.option("--response", "-r", "sort_by_response", is_flag=True,
              help="Sort by response efficiency")
@click.option("--limit", "-n", default=10, type=int,
              help="Number of results (default: 10)")
@click.option("--json", "output_json", is_flag=True,
              help="Output as JSON")
def top(sort_by_bounty: bool, sort_by_response: bool, limit: int, output_json: bool):
    """Show top programs by various metrics."""
    if sort_by_bounty:
        sort = "minimum_bounty"
        title = "Highest Bounties"
    elif sort_by_response:
        sort = "response_efficiency_percentage"
        title = "Fastest Response"
    else:
        sort = "resolved_report_count"
        title = "Most Resolved Reports"

    with H1Client() as client:
        try:
            programs = client.search_programs_graphql(
                filters=SearchFilters(paid=True),
                sort=sort,
                limit=limit,
            )
            total = len(programs)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    if output_json:
        print(json.dumps(
            {"total": total, "results": [
                {
                    "handle": p.handle,
                    "name": p.name,
                    "url": p.url,
                    "minimum_bounty": p.minimum_bounty,
                    "resolved_report_count": p.resolved_report_count,
                }
                for p in programs
            ]},
            indent=2,
        ))
        return

    table = Table(
        title=f"Top Programs — {title}",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Program", style="bold")
    table.add_column("Min Bounty", justify="right")
    table.add_column("Resolved", justify="right")
    table.add_column("Triage", justify="center", width=6)

    for i, p in enumerate(programs, 1):
        table.add_row(
            str(i),
            f"[link={p.url}]{p.name}[/link]\n[dim]{p.handle}[/dim]",
            _fmt_money(p.minimum_bounty, p.currency),
            str(p.resolved_report_count),
            _fmt_bool(p.triage_active),
        )

    console.print(table)


@main.command()
@click.option("--program", "-p", default=None,
              help="Filter by program handle (e.g. 'anthropic')")
@click.option("--limit", "-n", default=25, type=int,
              help="Number of results (default: 25)")
@click.option("--json", "output_json", is_flag=True,
              help="Output as JSON")
def hacktivity(program: str | None, limit: int, output_json: bool):
    """Browse publicly disclosed reports from HackerOne's hacktivity feed.

    Shows recently disclosed vulnerabilities with severity, bounty, and reporter info.

    \b
    Examples:
      h1 hacktivity                     Latest 25 disclosed reports
      h1 hacktivity -p anthropic        Only Anthropic's disclosed reports
      h1 hacktivity -n 10 --json        JSON output for scripting
    """
    with H1Client() as client:
        try:
            items = client.get_hacktivity(limit=limit, handle=program)
        except Exception as e:
            error_console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    if output_json:
        print(json.dumps([
            {
                "report_id": i.report_id,
                "title": i.title,
                "url": i.url,
                "severity": i.severity,
                "bounty_amount": i.bounty_amount,
                "currency": i.currency,
                "reporter": i.reporter_username,
                "program": i.program_handle,
                "program_name": i.program_name,
                "disclosed_at": i.disclosed_at,
            }
            for i in items
        ], indent=2))
        return

    if not items:
        console.print("[yellow]No hacktivity items found.[/yellow]")
        return

    title_str = "HackerOne Hacktivity"
    if program:
        title_str += f" — {program}"
    title_str += f" ({len(items)} items)"

    table = Table(
        title=title_str,
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Report", style="bold", max_width=50)
    table.add_column("Severity", justify="center")
    table.add_column("Bounty", justify="right")
    table.add_column("Program", max_width=20)
    table.add_column("Reporter")
    table.add_column("Disclosed", justify="right")

    for i, item in enumerate(items, 1):
        bounty = _fmt_money(
            int(item.bounty_amount) if item.bounty_amount else None,
            item.currency,
        )
        table.add_row(
            str(i),
            f"[link={item.url}]{item.title}[/link]",
            _fmt_severity(item.severity),
            bounty,
            f"[dim]{item.program_handle}[/dim]",
            item.reporter_username,
            _fmt_time_ago(item.disclosed_at),
        )

    console.print(table)


if __name__ == "__main__":
    main()
