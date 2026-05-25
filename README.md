# h1 — HackerOne CLI

A fast terminal client for HackerOne's bug bounty platform. Search programs, browse hacktivity, and pull scope/policy/bounty data — no API key, no browser.

```
$ h1 info 3cx -g

╭──── 3cx ────╮
│ 3CX         │
│ https://hackerone.com/3cx
│ A leading developer of unified communications...
╰──────────────╯
╭──── Guidelines ────╮
│ # Who we are       │
│ 3CX is a global    │
│ leader in business │
│ communications...  │
╰────────────────────╯
```

## Install

```bash
pip install git+https://github.com/overtimepog/h1-cli.git
```

Or from source:

```bash
git clone https://github.com/overtimepog/h1-cli.git
cd h1-cli
pip install -e ".[test]"
```

Installs the `h1` command globally.

## Usage

### `h1 info <handle>` — program deep-dive

```bash
h1 info anthropic              # Everything: stats, bounties, scope, policy
h1 info vercel -b              # Bounty table only (severity → payout)
h1 info stripe -s              # In-scope assets only
h1 info 3cx -g                 # Security policy / guidelines
h1 info anthropic -s -g        # Scope + guidelines combined
h1 info security --json | jq   # Machine-readable JSON
```

### `h1 search [keyword]` — find programs

```bash
h1 search android              # Keyword search
h1 search --paid               # Paid bounty programs only
h1 search --no-pay             # VDPs (no bounty)
h1 search --asset=google.com   # Programs with google.com in scope
h1 search --paid --min-bounty=500 --min-reports=100
h1 search --sort-by=bounty     # Sort by highest minimum bounty
h1 search --fast stripe        # Quick REST search (keyword only)
h1 search --json | jq '.results[] | {handle, minimum_bounty}'
```

### `h1 top` — leaderboards

```bash
h1 top                 # Most resolved reports (default)
h1 top --bounties      # Highest minimum bounties
h1 top --response      # Fastest response times
h1 top --bounties -n 20
```

### `h1 hacktivity` — disclosed reports

```bash
h1 hacktivity                  # Latest 25 publicly disclosed reports
h1 hacktivity -p anthropic     # Filter by program
h1 hacktivity -n 10            # Limit results
```

## How it works

Queries HackerOne's public GraphQL API at `hackerone.com/graphql`. No authentication needed — all data is publicly accessible. The CLI uses structured GraphQL filters for server-side filtering (asset, paid/VDP, keyword) and client-side filtering for fields the API doesn't support in `where` clauses (min bounty, min reports).

Rate-limited by HackerOne's standard API protections. Be a good citizen.

## Development

```bash
pip install -e ".[test]"
pytest                    # 71 tests
pytest --cov=src/h1cli    # with coverage
```

Built with Click + httpx + Rich. Tests use pytest-httpx for HTTP mocking and CliRunner for CLI integration tests.

## License

MIT
