# Packet Odyssey CLI

A lightweight, terminal-only edition of Packet Odyssey.

It simulates the journey of a synthetic web request through:

```text
Browser -> DNS -> TCP -> TLS -> Firewall -> Load Balancer -> API -> Database
```

The CLI sends no traffic to the URL you provide. The URL is parsed only as synthetic simulation input.

## Why this edition exists

The full Packet Odyssey project demonstrates React, FastAPI, PostgreSQL, containers, deployment, and observability. That is useful for a portfolio, but excessive when you only want the simulation engine.

This edition removes:

- React, Vite, and Node.js
- Browser UI and Nginx
- FastAPI and Uvicorn
- PostgreSQL and Alembic
- Prometheus, Grafana, Jaeger, and OpenTelemetry
- Long-running services

Runtime dependencies: **zero third-party packages**.

The optional history feature uses Python's built-in SQLite module.

## Requirements

- Python 3.11 or newer

## Run immediately without installation

Use the included single-file executable:

```bash
./dist/packet-odyssey.pyz doctor
./dist/packet-odyssey.pyz scenarios
./dist/packet-odyssey.pyz run --scenario successful-https
```

Or use the source launcher:

```bash
./packet-odyssey doctor
./packet-odyssey scenarios
./packet-odyssey run --scenario successful-https
```

You can also use the Python module directly:

```bash
PYTHONPATH=src python3 -m packet_odyssey run https://example.com
```

## Install as a user command

This dependency-free installer copies the source and creates a launcher in `~/.local/bin`:

```bash
./install.sh
```

Ensure `~/.local/bin` is on your `PATH`, then run:

```bash
packet-odyssey doctor
```

Install the included wheel without downloading any runtime or build dependency:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install dist/packet_odyssey_cli-0.1.0-py3-none-any.whl
packet-odyssey --help
```

For editable development, the project includes a tiny in-tree build backend:

```bash
python -m pip install -e . --no-build-isolation
```

## Common commands

### Healthy request

```bash
packet-odyssey run https://example.com/products
```

### Prepared scenario

```bash
packet-odyssey run --scenario expired-certificate
```

### Inject a failure

```bash
packet-odyssey run https://example.com --failure database_timeout
```

### Detailed technical output

```bash
packet-odyssey run --scenario tcp-packet-loss --mode technical
```

### Manual step-through

```bash
packet-odyssey run --scenario successful-https --step
```

### Machine-readable JSON

```bash
packet-odyssey run --scenario api-timeout --json --no-history
```

A blocking simulation failure returns exit code `2`, which makes the CLI useful in shell scripts.

### Export a run

```bash
packet-odyssey run --scenario dns-poisoning --export run.json
```

### Catalogue commands

```bash
packet-odyssey stages
packet-odyssey scenarios
packet-odyssey failures
```

### History and comparison

Runs are stored by default in:

```text
~/.local/share/packet-odyssey/history.db
```

Override the location with `PACKET_ODYSSEY_HISTORY`.

```bash
packet-odyssey history
packet-odyssey show RUN_ID
packet-odyssey compare RUN_ID_A RUN_ID_B
packet-odyssey clear-history
```

Disable storage for a run:

```bash
packet-odyssey run https://example.com --no-history
```

## Failure catalogue

- `dns_poisoning`
- `dns_timeout`
- `packet_loss`
- `connection_refused`
- `expired_certificate`
- `hostname_mismatch`
- `blocked_port`
- `rate_limited`
- `no_healthy_backend`
- `api_timeout`
- `database_timeout`
- `database_unavailable`

## Deterministic probability

A probability does not introduce unstable random tests. Packet Odyssey hashes the URL, scenario, failure, and optional seed to produce a reproducible decision.

```bash
packet-odyssey run https://example.com \
  --failure packet_loss \
  --probability 0.25 \
  --seed demo-1
```

## Docker

Docker is optional. The image is a single Python process, not a miniature data center wearing a trench coat.

```bash
docker build -t packet-odyssey-cli .
docker run --rm packet-odyssey-cli scenarios
docker run --rm packet-odyssey-cli run --scenario database-timeout --json --no-history
```

## Tests

No test framework needs to be installed:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Command succeeded or simulation completed |
| 1 | Invalid input, missing history item, or environment problem |
| 2 | Simulation ended in a blocking failure |

## Project layout

```text
Packet-Odyssey-CLI/
├── packet-odyssey
├── install.sh
├── src/packet_odyssey/
│   ├── cli.py
│   ├── engine.py
│   ├── catalog.py
│   ├── models.py
│   ├── render.py
│   ├── history.py
│   └── serialization.py
├── tests/
└── docs/
```

## Relationship to the full project

This is a separate CLI product, not Phase 7 of the web application. The full project remains useful as a systems and product portfolio piece. The CLI edition is intended for quick local use, teaching, shell automation, and environments where starting six containers to explain DNS would be considered a cry for help.
