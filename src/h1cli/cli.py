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

from .client import H1Client, Program


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


# ── CLI ──────────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0", prog_name="h1")
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
      h1 search google --json    JSON output for scripting
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("keyword", required=False, default="")
@click.option("--sort", "-s", default="resolved_report_count:descending",
              help="Sort order (default: resolved_report_count:descending)")
@click.option("--limit", "-n", default=25, type=int,
              help="Number of results (default: 25)")
@click.option("--json", "output_json", is_flag=True,
              help="Output as JSON")
@click.option("--filter", "-f", "filters_raw", multiple=True,
              help="Extra filters (e.g. 'minimum_bounty:>500')")
def search(keyword: str, sort: str, limit: int, output_json: bool,
           filters_raw: tuple[str, ...]):
    """Search HackerOne bounty programs.

    KEYWORD: optional search term to filter programs by name/handle.
    """
    filters = {}
    for f in filters_raw:
        if ":" in f:
            k, v = f.split(":", 1)
            filters[k.strip()] = v.strip()

    with H1Client() as client:
        try:
            programs, total = client.search_programs(
                query=keyword, sort=sort, limit=limit, filters=filters or None
            )
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
                }
                for p in programs
            ]},
            indent=2,
        ))
        return

    if not programs:
        console.print(f"[yellow]No programs found[/yellow] ({total} total)")
        return

    table = Table(
        title=f"HackerOne Programs ({total} total, showing {len(programs)})",
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
@click.option("--json", "output_json", is_flag=True,
              help="Output as JSON")
def info(handle: str, bounties: bool, scope: bool, output_json: bool):
    """Show detailed info about a program by handle.

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
        }, indent=2))
        return

    # ── Header ───────────────────────────────────────────────────────
    header = Text()
    header.append(f"{program.name}", style="bold cyan")
    header.append(f"\n{program.url}", style="dim link={program.url}")
    if program.about:
        header.append(f"\n\n{program.about}", style="italic")
    console.print(Panel(header, title=f"[bold]{program.handle}[/bold]", border_style="cyan"))

    # ── Stats table ──────────────────────────────────────────────────
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
    if bounties and program.bounty_table:
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
            name = row.get("name", "—")
            severities = {
                "critical": ("critical_minimum", "critical"),
                "high": ("high_minimum", "high"),
                "medium": ("medium_minimum", "medium"),
                "low": ("low_minimum", "low"),
            }
            # Check if this row uses severity columns
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
                # Simple row with just a name
                bt_table.add_row(name, "—", "—")

        console.print(bt_table)

    # ── Scope ────────────────────────────────────────────────────────
    if scope and program.scopes:
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
        sort = "minimum_bounty:descending"
        title = "Highest Bounties"
    elif sort_by_response:
        sort = "response_efficiency_percentage:ascending"
        title = "Fastest Response"
    else:
        sort = "resolved_report_count:descending"
        title = "Most Resolved Reports"

    with H1Client() as client:
        try:
            programs, total = client.search_programs(sort=sort, limit=limit)
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


if __name__ == "__main__":
    main()
