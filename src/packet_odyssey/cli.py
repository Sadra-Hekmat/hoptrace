from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

from . import __version__
from .catalog import FAILURES, SCENARIOS, SCENARIO_BY_ID, STAGE_ORDER, STAGES
from .engine import SimulationConfigurationError, SimulationEngine
from .history import HistoryStore, default_history_path
from .models import FailureType, SimulationConfig, SimulationStatus, StageStatus
from .render import Palette, colors_enabled, print_banner, print_stage, print_summary, render_saved_run
from .serialization import dumps, to_primitive


def enum_choice(enum_type: type[FailureType], value: str) -> FailureType:
    try:
        return enum_type(value)
    except ValueError as exc:
        valid = ", ".join(item.value for item in enum_type)
        raise argparse.ArgumentTypeError(f"invalid choice: {value!r} (choose from {valid})") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="packet-odyssey",
        description="Simulate a synthetic web request from browser to database.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run a simulation.")
    run.add_argument("url", nargs="?", help="Synthetic HTTP or HTTPS URL.")
    run.add_argument("--scenario", choices=sorted(SCENARIO_BY_ID), help="Use a prepared scenario.")
    run.add_argument("--failure", type=lambda value: enum_choice(FailureType, value), help="Inject one failure.")
    run.add_argument("--probability", type=float, help="Deterministic failure probability from 0 to 1.")
    run.add_argument("--delay-ms", type=int, help="Override the failure's added synthetic delay.")
    run.add_argument("--seed", default="", help="Change deterministic probability sampling.")
    run.add_argument("--mode", choices=("compact", "guided", "technical"), default="guided")
    run.add_argument("--step", action="store_true", help="Wait for Enter after each executed stage.")
    run.add_argument("--real-time", action="store_true", help="Sleep according to synthetic stage duration.")
    run.add_argument("--speed", type=float, choices=(0.5, 1, 2, 4), default=1)
    run.add_argument("--json", action="store_true", help="Print only machine-readable JSON.")
    run.add_argument("--export", type=Path, help="Write the completed run as JSON.")
    run.add_argument("--no-history", action="store_true", help="Do not store this run in SQLite history.")
    run.add_argument("--ascii", action="store_true", help="Use ASCII-only status symbols.")

    scenarios = subparsers.add_parser("scenarios", help="List predefined scenarios.")
    scenarios.add_argument("--json", action="store_true")

    stages = subparsers.add_parser("stages", help="List simulation stages.")
    stages.add_argument("--json", action="store_true")

    failures = subparsers.add_parser("failures", help="List available failures.")
    failures.add_argument("--json", action="store_true")

    history = subparsers.add_parser("history", help="List stored runs.")
    history.add_argument("--limit", type=int, default=20)
    history.add_argument("--json", action="store_true")

    show = subparsers.add_parser("show", help="Show one stored run.")
    show.add_argument("run_id")
    show.add_argument("--json", action="store_true")

    compare = subparsers.add_parser("compare", help="Compare two stored runs.")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--json", action="store_true")

    clear = subparsers.add_parser("clear-history", help="Delete stored runs.")
    clear.add_argument("--yes", action="store_true", help="Skip confirmation.")

    subparsers.add_parser("doctor", help="Check the local CLI environment.")
    return parser


def resolve_run(args: argparse.Namespace) -> tuple[str, str | None, FailureType | None]:
    scenario = SCENARIO_BY_ID.get(args.scenario) if args.scenario else None
    if args.url:
        url = args.url
    elif scenario:
        url = scenario.url
    else:
        url = SCENARIO_BY_ID["successful-https"].url
    failure = args.failure if args.failure is not None else scenario.failure if scenario else None
    return url, scenario.id if scenario else None, failure


def command_run(args: argparse.Namespace, palette: Palette) -> int:
    url, scenario_id, failure_type = resolve_run(args)
    config = SimulationConfig(
        url=url,
        scenario_id=scenario_id,
        failure_type=failure_type,
        probability=args.probability,
        delay_ms=args.delay_ms,
        seed=args.seed,
    )
    if args.json and args.step:
        print("error: --step cannot be combined with --json", file=sys.stderr)
        return 1
    if failure_type is None and (args.probability is not None or args.delay_ms is not None):
        print("error: --probability and --delay-ms require a failure or failure scenario", file=sys.stderr)
        return 1

    engine = SimulationEngine()
    try:
        session = engine.start(config)
    except SimulationConfigurationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.json:
        print_banner(palette)
        print(f"URL:      {url}")
        print(f"Scenario: {scenario_id or 'custom'}")
        print(f"Failure:  {failure_type.value if failure_type else 'none'}")
        print()

    for result in session:
        if not args.json:
            print_stage(result, args.mode, palette, args.ascii)
        if args.real_time and result.duration_ms:
            time.sleep(result.duration_ms / 1000 / args.speed)
        if args.step and result.status is not StageStatus.SKIPPED:
            try:
                input("Press Enter for the next stage...")
            except EOFError:
                pass

    run = session.finish()
    history_saved = False
    if not args.no_history:
        try:
            HistoryStore().save(run)
            history_saved = True
        except (OSError, ValueError) as exc:
            print(f"warning: history could not be saved: {exc}", file=sys.stderr)

    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(dumps(run) + "\n", encoding="utf-8")

    if args.json:
        print(dumps(run))
    else:
        print_summary(run, palette)
        if history_saved:
            print(f"  History DB:     {default_history_path()}")
        if args.export:
            print(f"  Exported:       {args.export}")

    return 0 if run.status is SimulationStatus.COMPLETED else 2


def command_scenarios(args: argparse.Namespace, palette: Palette) -> int:
    if args.json:
        print(dumps(SCENARIOS))
        return 0
    print(palette.bold("Scenarios"))
    for scenario in SCENARIOS:
        failure = scenario.failure.value if scenario.failure else "none"
        print(f"  {scenario.id:<24} {scenario.name}")
        print(f"    {scenario.description}")
        print(f"    failure={failure}; expected={scenario.expected_status.value}")
    return 0


def command_stages(args: argparse.Namespace, palette: Palette) -> int:
    payload = [STAGES[stage] for stage in STAGE_ORDER]
    if args.json:
        serializable = [
            {
                "id": stage.id.value,
                "label": stage.label,
                "protocol": stage.protocol,
                "base_duration_ms": stage.base_duration_ms,
                "simple_explanation": stage.simple_explanation,
                "technical_explanation": stage.technical_explanation,
            }
            for stage in payload
        ]
        print(dumps(serializable))
        return 0
    print(palette.bold("Stages"))
    for index, stage in enumerate(payload, start=1):
        print(f"  {index}. {stage.label:<20} {stage.protocol:<14} {stage.base_duration_ms} ms")
        print(f"     {stage.simple_explanation}")
    return 0


def command_failures(args: argparse.Namespace, palette: Palette) -> int:
    if args.json:
        print(dumps(list(FAILURES.values())))
        return 0
    print(palette.bold("Failures"))
    for definition in FAILURES.values():
        kind = "blocking" if definition.blocking else "recoverable"
        print(f"  {definition.type.value:<24} stage={definition.stage.value:<16} {kind}")
        print(f"    {definition.symptom}")
    return 0


def command_history(args: argparse.Namespace, palette: Palette) -> int:
    rows = HistoryStore().list(max(1, min(args.limit, 500)))
    if args.json:
        print(dumps(rows))
        return 0
    print(palette.bold(f"History ({len(rows)} runs)"))
    if not rows:
        print("  No runs stored.")
        return 0
    for row in rows:
        print(
            f"  {row['id']}  {row['status']:<9} {row['terminal_stage']:<16} "
            f"{row['total_duration_ms']:>5} ms  {row['url']}"
        )
    return 0


def command_show(args: argparse.Namespace, palette: Palette) -> int:
    payload = HistoryStore().get(args.run_id)
    if payload is None:
        print(f"error: run {args.run_id!r} was not found", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        render_saved_run(payload, palette)
    return 0


def comparison_payload(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_stages = {stage["stage"]: stage for stage in left["stages"]}
    right_stages = {stage["stage"]: stage for stage in right["stages"]}
    stages: list[dict[str, Any]] = []
    for stage in (item.value for item in STAGE_ORDER):
        lstage = left_stages[stage]
        rstage = right_stages[stage]
        lduration = lstage["duration_ms"]
        rduration = rstage["duration_ms"]
        delta = rduration - lduration if lduration is not None and rduration is not None else None
        stages.append({
            "stage": stage,
            "left_status": lstage["status"],
            "right_status": rstage["status"],
            "left_duration_ms": lduration,
            "right_duration_ms": rduration,
            "duration_delta_ms": delta,
        })
    return {
        "left": {key: left.get(key) for key in ("id", "status", "scenario_id", "failure_type", "total_duration_ms")},
        "right": {key: right.get(key) for key in ("id", "status", "scenario_id", "failure_type", "total_duration_ms")},
        "stages": stages,
    }


def command_compare(args: argparse.Namespace, palette: Palette) -> int:
    store = HistoryStore()
    left = store.get(args.left)
    right = store.get(args.right)
    if left is None or right is None:
        missing = args.left if left is None else args.right
        print(f"error: run {missing!r} was not found", file=sys.stderr)
        return 1
    payload = comparison_payload(left, right)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(palette.bold("Run comparison"))
    print(f"  left:  {args.left} ({left['status']}, {left['total_duration_ms']} ms)")
    print(f"  right: {args.right} ({right['status']}, {right['total_duration_ms']} ms)")
    print()
    print("  Stage             Left       Right      Delta")
    for stage in payload["stages"]:
        delta = f"{stage['duration_delta_ms']:+d} ms" if stage["duration_delta_ms"] is not None else "-"
        print(f"  {stage['stage']:<17} {stage['left_status']:<10} {stage['right_status']:<10} {delta}")
    return 0


def command_clear(args: argparse.Namespace) -> int:
    if not args.yes:
        try:
            answer = input(f"Delete all runs from {default_history_path()}? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in {"y", "yes"}:
            print("Cancelled.")
            return 0
    count = HistoryStore().clear()
    print(f"Deleted {count} run(s).")
    return 0


def command_doctor(palette: Palette) -> int:
    compatible = sys.version_info >= (3, 11)
    print(palette.bold("Packet Odyssey doctor"))
    print(f"  CLI version:    {__version__}")
    print(f"  Python:         {platform.python_version()} {'OK' if compatible else 'UNSUPPORTED'}")
    print(f"  Platform:       {platform.platform()}")
    print(f"  Runtime deps:   none")
    print(f"  History DB:     {default_history_path()}")
    print(f"  Color output:   {'enabled' if colors_enabled(False) else 'disabled'}")
    return 0 if compatible else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    palette = Palette(colors_enabled(args.no_color))
    commands = {
        "run": command_run,
        "scenarios": command_scenarios,
        "stages": command_stages,
        "failures": command_failures,
        "history": command_history,
        "show": command_show,
        "compare": command_compare,
        "clear-history": command_clear,
    }
    if args.command == "doctor":
        return command_doctor(palette)
    return commands[args.command](args, palette)


def entrypoint() -> None:
    raise SystemExit(main())
