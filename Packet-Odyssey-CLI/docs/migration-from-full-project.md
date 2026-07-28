# Migration from the Full Packet Odyssey Project

The CLI edition is intentionally separate from the React and FastAPI repository.

## Preserved

- Eight-stage request path
- Deterministic execution
- Twelve failure definitions
- Blocking and recoverable failure behavior
- Downstream skipped stages
- Guided and technical explanations
- Structured event timeline
- Scenario catalogue
- Persistent run history and comparison

## Removed

- React frontend
- FastAPI HTTP layer
- Node workspaces
- Pydantic contracts
- SQLAlchemy and Alembic
- PostgreSQL service
- Nginx reverse proxy
- Prometheus, Grafana, Jaeger, and OTLP
- Azure deployment assets

## Equivalent workflows

| Full project | CLI edition |
|---|---|
| Open the simulator UI | `packet-odyssey run` |
| Choose a scenario | `--scenario ID` |
| Open technical mode | `--mode technical` |
| Manual playback | `--step` |
| API JSON response | `--json` |
| Run history panel | `packet-odyssey history` |
| Run comparison panel | `packet-odyssey compare` |

The full repository should remain intact if it is part of your portfolio. Use this CLI repository when deployment size, startup time, or shell automation matters more than visual presentation.
