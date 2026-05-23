# h1cli

HackerOne bounty program CLI — search, browse, and analyze bug bounty programs right from your terminal.

No API key required. Uses HackerOne's public GraphQL and REST APIs.

## Install

```bash
pip install git+https://github.com/overtimepog/h1cli.git
```

Or from source:

```bash
git clone https://github.com/overtimepog/h1cli.git
cd h1cli
pip install -e ".[test]"
```

## Commands

| Command | Description |
|---|---|
| `h1 search [keyword]` | Search programs with powerful filters |
| `h1 info <handle>` | Detailed program info, bounty table, scope |
| `h1 top` | Top programs by reports, bounties, or response time |
| `h1 hacktivity` | Browse publicly disclosed vulnerability reports |
| `h1 policy <handle>` | Read a program's security policy and guidelines |

## Usage

### Search programs

```bash
# Keyword search
h1 search android

# Filter by asset in scope
h1 search --asset=google.com

# Paid programs only
h1 search --paid

# VDPs (no bounty)
h1 search --no-pay

# Minimum bounty filter
h1 search --paid --min-bounty=500

# Established programs (100+ resolved reports)
h1 search --min-reports=100

# Sort by bounty or response time
h1 search --sort-by=bounty
h1 search --sort-by=response

# Combine filters
h1 search --paid --asset=api.example.com --min-bounty=1000

# JSON output for scripting
h1 search --json | jq '.results[].handle'

# Fast REST search (keyword only)
h1 search --fast stripe
```

### Program info

```bash
# Basic info
h1 info anthropic

# Show bounty table (severity → payout)
h1 info anthropic --bounties

# Show in-scope assets
h1 info vercel --scope

# JSON output
h1 info anthropic --json
```

### Top programs

```bash
# Most resolved reports (default)
h1 top

# Highest minimum bounties
h1 top --bounties

# Fastest response time
h1 top --response

# Limit results
h1 top --bounties -n 20
```

### Hacktivity feed

```bash
# Latest 25 publicly disclosed reports
h1 hacktivity

# Filter by program
h1 hacktivity -p anthropic

# Limit results
h1 hacktivity -n 10

# JSON output
h1 hacktivity -p vercel --json
```

### Policy viewer

```bash
# Read a program's security policy
h1 policy anthropic

# JSON output
h1 policy vercel --json
```

## Features

- **No auth needed** — uses HackerOne's public GraphQL and REST APIs
- **Rich terminal output** — tables, colors, formatting via `rich`
- **Structured search filters** — filter by asset, paid/VDP, min bounty, min reports
- **Hacktivity feed** — browse publicly disclosed reports with severity, bounty, reporter info
- **Policy viewer** — read program guidelines, scope, and out-of-scope rules
- **Bounty tables** — severity → payout mappings with `--bounties`
- **Scope listing** — in-scope assets with `--scope`
- **JSON output** — pipe into `jq` or other tools with `--json` on every command
- **Color-coded severities** — critical (red), high, medium (yellow), low (green)

## Development

```bash
# Install with test deps
pip install -e ".[test]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/h1cli
```

## License

MIT
