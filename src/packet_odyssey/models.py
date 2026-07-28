from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable
from urllib.parse import SplitResult


class SimulationStage(StrEnum):
    BROWSER = "browser"
    DNS = "dns"
    TCP = "tcp"
    TLS = "tls"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    API = "api"
    DATABASE = "database"


class StageStatus(StrEnum):
    IDLE = "idle"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class SimulationStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class EventSeverity(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class FailureType(StrEnum):
    DNS_POISONING = "dns_poisoning"
    DNS_TIMEOUT = "dns_timeout"
    PACKET_LOSS = "packet_loss"
    CONNECTION_REFUSED = "connection_refused"
    EXPIRED_CERTIFICATE = "expired_certificate"
    HOSTNAME_MISMATCH = "hostname_mismatch"
    BLOCKED_PORT = "blocked_port"
    RATE_LIMITED = "rate_limited"
    NO_HEALTHY_BACKEND = "no_healthy_backend"
    API_TIMEOUT = "api_timeout"
    DATABASE_TIMEOUT = "database_timeout"
    DATABASE_UNAVAILABLE = "database_unavailable"


JsonFactory = Callable[[SplitResult], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class StageDefinition:
    id: SimulationStage
    label: str
    protocol: str
    simple_explanation: str
    technical_explanation: str
    base_duration_ms: int
    input_factory: JsonFactory
    output_factory: JsonFactory


@dataclass(frozen=True, slots=True)
class FailureDefinition:
    type: FailureType
    title: str
    stage: SimulationStage
    severity: EventSeverity
    blocking: bool
    symptom: str
    explanation: str
    technical_explanation: str
    troubleshooting: tuple[str, ...]
    event_type: str
    event_message: str
    output: dict[str, Any]
    stage_status: StageStatus
    added_delay_ms: int


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    id: str
    name: str
    description: str
    learning_objective: str
    url: str
    failure: FailureType | None
    expected_status: SimulationStatus
    expected_terminal_stage: SimulationStage
    observable_symptom: str


@dataclass(slots=True)
class SimulationEvent:
    id: str
    sequence: int
    stage: SimulationStage
    type: str
    severity: EventSeverity
    message: str
    started_at: int
    completed_at: int | None = None
    duration_ms: int | None = None
    technical_details: dict[str, Any] | None = None


@dataclass(slots=True)
class StageResult:
    stage: SimulationStage
    label: str
    protocol: str
    status: StageStatus
    input: dict[str, Any]
    output: dict[str, Any] | None
    duration_ms: int | None
    continue_execution: bool
    failure_type: FailureType | None = None
    event_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    url: str
    scenario_id: str | None = None
    failure_type: FailureType | None = None
    probability: float | None = None
    delay_ms: int | None = None
    seed: str = ""


@dataclass(slots=True)
class SimulationRun:
    id: str
    status: SimulationStatus
    url: str
    scenario_id: str | None
    failure_type: FailureType | None
    stages: list[StageResult]
    events: list[SimulationEvent]
    started_at: int
    completed_at: int
    total_duration_ms: int
    terminal_stage: SimulationStage
    failure_triggered: bool
