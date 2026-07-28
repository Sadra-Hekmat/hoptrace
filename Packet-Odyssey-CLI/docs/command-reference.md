# Command Reference

## `run`

```text
packet-odyssey run [URL]
  [--scenario ID]
  [--failure TYPE]
  [--probability 0..1]
  [--delay-ms N]
  [--seed TEXT]
  [--mode compact|guided|technical]
  [--step]
  [--real-time]
  [--speed 0.5|1|2|4]
  [--json]
  [--export PATH]
  [--no-history]
  [--ascii]
```

When neither a URL nor scenario is supplied, the healthy HTTPS scenario is used.

An explicit `--failure` overrides the failure attached to a selected scenario.

## Catalogue

```text
packet-odyssey scenarios [--json]
packet-odyssey stages [--json]
packet-odyssey failures [--json]
```

## History

```text
packet-odyssey history [--limit N] [--json]
packet-odyssey show RUN_ID [--json]
packet-odyssey compare LEFT_ID RIGHT_ID [--json]
packet-odyssey clear-history [--yes]
```

## Environment

- `PACKET_ODYSSEY_HISTORY`: explicit SQLite path.
- `XDG_DATA_HOME`: base path when an explicit history path is absent.
- `NO_COLOR`: disables ANSI color.
