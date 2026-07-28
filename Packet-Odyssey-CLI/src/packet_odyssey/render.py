from __future__ import annotations

import json
import os
import sys
from typing import Any

from .catalog import FAILURES, STAGES
from .models import SimulationRun, StageResult, StageStatus


class Palette:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def apply(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return self.apply("1", text)

    def green(self, text: str) -> str:
        return self.apply("32", text)

    def yellow(self, text: str) -> str:
        return self.apply("33", text)

    def red(self, text: str) -> str:
        return self.apply("31", text)

    def cyan(self, text: str) -> str:
        return self.apply("36", text)

    def dim(self, text: str) -> str:
        return self.apply("2", text)


def colors_enabled(disabled: bool = False) -> bool:
    return not disabled and "NO_COLOR" not in os.environ and sys.stdout.isatty()


def format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    return str(value)


def status_symbol(status: StageStatus, ascii_only: bool = False) -> str:
    symbols = {
        StageStatus.SUCCESS: "OK" if ascii_only else "✓",
        StageStatus.WARNING: "!!" if ascii_only else "!",
        StageStatus.FAILED: "XX" if ascii_only else "✗",
        StageStatus.SKIPPED: "--" if ascii_only else "·",
        StageStatus.IDLE: ".." if ascii_only else "○",
    }
    return symbols[status]


def status_text(result: StageResult, palette: Palette, ascii_only: bool = False) -> str:
    symbol = status_symbol(result.status, ascii_only)
    value = f"[{symbol}]"
    if result.status is StageStatus.SUCCESS:
        return palette.green(value)
    if result.status is StageStatus.WARNING:
        return palette.yellow(value)
    if result.status is StageStatus.FAILED:
        return palette.red(value)
    return palette.dim(value)


def print_banner(palette: Palette) -> None:
    print(palette.bold("Packet Odyssey CLI"))
    print(palette.dim("Browser -> DNS -> TCP -> TLS -> Firewall -> Load Balancer -> API -> Database"))
    print()


def print_stage(result: StageResult, mode: str, palette: Palette, ascii_only: bool = False) -> None:
    duration = f"{result.duration_ms} ms" if result.duration_ms is not None else "not executed"
    print(f"{status_text(result, palette, ascii_only)} {palette.bold(result.label)}  {palette.dim(result.protocol)}  {duration}")
    if result.status is StageStatus.SKIPPED:
        print(f"    {palette.dim('Skipped because an earlier blocking failure stopped the request.')}" )
        return

    definition = STAGES[result.stage]
    if mode == "guided":
        print(f"    {definition.simple_explanation}")
    elif mode == "technical":
        print(f"    {definition.technical_explanation}")
        print(f"    input:  {format_value(result.input)}")
        print(f"    output: {format_value(result.output)}")

    if result.failure_type:
        failure = FAILURES[result.failure_type]
        print(f"    {palette.red('Failure') if failure.blocking else palette.yellow('Warning')}: {failure.title}")
        print(f"    Symptom: {failure.symptom}")
        explanation = failure.technical_explanation if mode == "technical" else failure.explanation
        print(f"    Cause: {explanation}")
        if mode != "compact":
            print("    Troubleshooting:")
            for item in failure.troubleshooting:
                print(f"      - {item}")
    print()


def print_summary(run: SimulationRun, palette: Palette) -> None:
    print(palette.bold("Summary"))
    status = palette.green(run.status.value.upper()) if run.status.value == "completed" else palette.red(run.status.value.upper())
    print(f"  Status:         {status}")
    print(f"  Run ID:         {run.id}")
    print(f"  Terminal stage: {run.terminal_stage.value}")
    print(f"  Synthetic time: {run.total_duration_ms} ms")
    print(f"  Events:         {len(run.events)}")
    if run.failure_type:
        print(f"  Failure:        {run.failure_type.value}")
    elif not run.failure_triggered and any(stage.status is StageStatus.WARNING for stage in run.stages):
        print("  Result:         completed with warning")


def render_saved_run(payload: dict[str, Any], palette: Palette) -> None:
    print(palette.bold(f"Run {payload['id']}"))
    print(f"  Status:         {payload['status']}")
    print(f"  URL:            {payload['url']}")
    print(f"  Scenario:       {payload.get('scenario_id') or '-'}")
    print(f"  Failure:        {payload.get('failure_type') or '-'}")
    print(f"  Terminal stage: {payload['terminal_stage']}")
    print(f"  Synthetic time: {payload['total_duration_ms']} ms")
    print()
    for stage in payload["stages"]:
        duration = f"{stage['duration_ms']} ms" if stage["duration_ms"] is not None else "-"
        print(f"  {stage['stage']:<16} {stage['status']:<8} {duration}")
