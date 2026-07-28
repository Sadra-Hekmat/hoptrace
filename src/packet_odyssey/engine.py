from __future__ import annotations

import hashlib
import time
from collections.abc import Iterator
from urllib.parse import urlsplit
from uuid import uuid4

from .catalog import FAILURES, STAGE_ORDER, STAGES
from .models import (
    EventSeverity,
    FailureDefinition,
    SimulationConfig,
    SimulationEvent,
    SimulationRun,
    SimulationStage,
    SimulationStatus,
    StageResult,
    StageStatus,
)


class SimulationConfigurationError(ValueError):
    """Raised when simulation input is invalid."""


def validate_url(value: str) -> str:
    candidate = value.strip()
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise SimulationConfigurationError("Only HTTP and HTTPS URLs are supported.")
    if not parsed.hostname:
        raise SimulationConfigurationError("The URL must include a hostname.")
    if parsed.username or parsed.password:
        raise SimulationConfigurationError("URLs containing credentials are not supported.")
    if len(candidate) > 2048:
        raise SimulationConfigurationError("The URL must not exceed 2048 characters.")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise SimulationConfigurationError(f"Invalid URL port: {exc}") from exc
    return candidate


class SimulationSession:
    def __init__(self, config: SimulationConfig) -> None:
        validated = validate_url(config.url)
        if config.probability is not None and not 0 <= config.probability <= 1:
            raise SimulationConfigurationError("Failure probability must be between 0 and 1.")
        if config.delay_ms is not None and not 0 <= config.delay_ms <= 60_000:
            raise SimulationConfigurationError("Failure delay must be between 0 and 60000 ms.")
        self.config = SimulationConfig(
            url=validated,
            scenario_id=config.scenario_id,
            failure_type=config.failure_type,
            probability=config.probability,
            delay_ms=config.delay_ms,
            seed=config.seed,
        )
        self.run_id = f"run-{uuid4()}"
        self.started_at = int(time.time() * 1000)
        self.current_time = self.started_at
        self.stages: list[StageResult] = []
        self.events: list[SimulationEvent] = []
        self.failure_triggered = False
        self._finished = False
        self._generator = self._execute()

    def __iter__(self) -> Iterator[StageResult]:
        return self

    def __next__(self) -> StageResult:
        return next(self._generator)

    def _event(
        self,
        stage: SimulationStage,
        event_type: str,
        severity: EventSeverity,
        message: str,
        duration_ms: int | None = None,
        details: dict[str, object] | None = None,
    ) -> SimulationEvent:
        event = SimulationEvent(
            id=f"event-{uuid4()}",
            sequence=len(self.events) + 1,
            stage=stage,
            type=event_type,
            severity=severity,
            message=message,
            started_at=self.current_time,
            completed_at=self.current_time + duration_ms if duration_ms is not None else None,
            duration_ms=duration_ms,
            technical_details=details,
        )
        self.events.append(event)
        return event

    def _failure_applies(self, definition: FailureDefinition) -> bool:
        probability = self.config.probability
        if probability is None:
            return True
        material = (
            f"{self.config.url}|{self.config.scenario_id or ''}|"
            f"{definition.type.value}|{self.config.seed}"
        )
        digest = hashlib.sha256(material.encode("utf-8")).digest()
        sample = int.from_bytes(digest[:8], "big") / 2**64
        return sample < probability

    def _execute(self) -> Iterator[StageResult]:
        parsed = urlsplit(self.config.url)
        failure = FAILURES.get(self.config.failure_type) if self.config.failure_type else None
        blocked = False

        for stage in STAGE_ORDER:
            definition = STAGES[stage]
            if blocked:
                skipped = StageResult(
                    stage=stage,
                    label=definition.label,
                    protocol=definition.protocol,
                    status=StageStatus.SKIPPED,
                    input={},
                    output=None,
                    duration_ms=None,
                    continue_execution=False,
                )
                self.stages.append(skipped)
                yield skipped
                continue

            started = self._event(
                stage,
                f"{stage.value}.started",
                EventSeverity.INFO,
                f"{definition.label} started.",
                details={"protocol": definition.protocol},
            )
            stage_input = definition.input_factory(parsed)
            stage_output = definition.output_factory(parsed)
            active_failure = failure if failure and failure.stage == stage and self._failure_applies(failure) else None

            if active_failure:
                self.failure_triggered = True
                stage_output.update(active_failure.output)
                duration = definition.base_duration_ms + (
                    self.config.delay_ms if self.config.delay_ms is not None else active_failure.added_delay_ms
                )
                completed = self._event(
                    stage,
                    active_failure.event_type,
                    active_failure.severity,
                    active_failure.event_message,
                    duration,
                    stage_output,
                )
                result = StageResult(
                    stage=stage,
                    label=definition.label,
                    protocol=definition.protocol,
                    status=active_failure.stage_status,
                    input=stage_input,
                    output=stage_output,
                    duration_ms=duration,
                    continue_execution=not active_failure.blocking,
                    failure_type=active_failure.type,
                    event_ids=[started.id, completed.id],
                )
                blocked = active_failure.blocking
            else:
                duration = definition.base_duration_ms
                completed = self._event(
                    stage,
                    f"{stage.value}.completed",
                    EventSeverity.SUCCESS,
                    f"{definition.label} completed successfully.",
                    duration,
                    stage_output,
                )
                result = StageResult(
                    stage=stage,
                    label=definition.label,
                    protocol=definition.protocol,
                    status=StageStatus.SUCCESS,
                    input=stage_input,
                    output=stage_output,
                    duration_ms=duration,
                    continue_execution=True,
                    event_ids=[started.id, completed.id],
                )

            self.stages.append(result)
            self.current_time += duration
            yield result

        self._finished = True

    def finish(self) -> SimulationRun:
        if not self._finished:
            for _ in self:
                pass
        failed_stage = next((stage for stage in self.stages if stage.status is StageStatus.FAILED), None)
        terminal = failed_stage.stage if failed_stage else SimulationStage.DATABASE
        status = SimulationStatus.FAILED if failed_stage else SimulationStatus.COMPLETED
        total = sum(stage.duration_ms or 0 for stage in self.stages)
        return SimulationRun(
            id=self.run_id,
            status=status,
            url=self.config.url,
            scenario_id=self.config.scenario_id,
            failure_type=self.config.failure_type if self.failure_triggered else None,
            stages=self.stages,
            events=self.events,
            started_at=self.started_at,
            completed_at=self.started_at + total,
            total_duration_ms=total,
            terminal_stage=terminal,
            failure_triggered=self.failure_triggered,
        )


class SimulationEngine:
    def start(self, config: SimulationConfig) -> SimulationSession:
        return SimulationSession(config)

    def run(self, config: SimulationConfig) -> SimulationRun:
        session = self.start(config)
        return session.finish()
