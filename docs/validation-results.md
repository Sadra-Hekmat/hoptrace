# Validation Results

## Release

Packet Odyssey CLI `0.1.0`

## Runtime

- Python used for release validation: 3.13.5
- Declared compatibility: Python 3.11+
- Third-party runtime dependencies: none

## Completed checks

| Check | Result |
|---|---|
| Python bytecode compilation | Passed |
| Standard-library unit tests | 8 passed |
| Healthy eight-stage run | Passed |
| Blocking TLS failure | Passed |
| Recoverable TCP warning | Passed |
| Deterministic probability | Passed |
| JSON output parsing | Passed |
| Exit code 2 for blocking failure | Passed |
| SQLite save/list/get/clear | Passed |
| Stored-run comparison | Passed |
| Dependency-free shell installer | Passed |
| Editable PEP 517 installation | Passed |
| Offline wheel installation | Passed |
| Single-file zipapp execution | Passed |
| Catalogue counts | 8 stages, 8 scenarios, 12 failures |

## Commands used

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
./packet-odyssey doctor
./packet-odyssey run --scenario successful-https --no-history
./packet-odyssey run --scenario expired-certificate --json --no-history
./dist/packet-odyssey.pyz run --scenario dns-poisoning --json --no-history
python -m pip install dist/packet_odyssey_cli-0.1.0-py3-none-any.whl --no-index
```

## Safety validation

The source imports no HTTP client, DNS resolver, socket workflow, packet-capture library, TLS scanner, or database driver. The SQLite module is used only for local CLI history.
