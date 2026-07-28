# CLI Architecture

## Goals

- Preserve the educational simulation model.
- Require only Python 3.11+ at runtime.
- Start instantly without a server.
- Work interactively and in automation.
- Keep output reproducible.
- Avoid network access and unsafe real-world probing.

## Components

```text
argparse CLI
    |
    +-- catalogue commands
    |
    +-- simulation engine
    |     +-- stage definitions
    |     +-- failure definitions
    |     +-- deterministic probability
    |     +-- structured events
    |
    +-- terminal renderer
    |
    +-- JSON serializer
    |
    +-- optional sqlite3 history
```

## Runtime boundary

The URL is parsed with `urllib.parse`. The CLI does not resolve DNS, open sockets, validate certificates, call APIs, or connect to a database.

## Persistence

History uses the Python standard library `sqlite3` module. It stores the complete JSON payload for each run plus indexed summary fields. Persistence can be disabled with `--no-history`.

## Output modes

- `compact`: one status line per stage.
- `guided`: beginner explanation and failure diagnosis.
- `technical`: protocol details plus structured stage input and output.
- `--json`: no decorative text, suitable for scripts.

## Exit behavior

A simulated blocking failure is a valid simulation result, but the `run` command exits with code 2 so shell automation can distinguish it from a healthy path. Configuration and operational errors use code 1.
