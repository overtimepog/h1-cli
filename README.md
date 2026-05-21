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

## Usage

```bash
# Search for programs
h1 search android
h1 search google --sort minimum_bounty:descending
h1 search --json  # JSON output for scripting

# Get detailed info on a program
h1 info anthropic
h1 info anthropic --bounties  # Show bounty table
h1 info anthropic --scope     # Show in-scope assets

# Top programs
h1 top                  # Most resolved reports
h1 top --bounties       # Highest minimum bounties
h1 top --response       # Fastest response time
```

## Commands

| Command | Description |
|---------|-------------|
| `h1 search [keyword]` | Search programs by name/handle |
| `h1 info <handle>` | Detailed program info |
| `h1 top` | Top programs by various metrics |

## Features

- **No auth needed** — uses HackerOne's public API
- **Rich terminal output** — tables, colors, formatting via `rich`
- **JSON output** — pipe into `jq` or other tools with `--json`
- **Bounty tables** — see severity → payout mappings with `--bounties`
- **Scope listing** — see in-scope assets with `--scope`
- **Filtering** — custom search filters with `--filter`

## License

MIT
