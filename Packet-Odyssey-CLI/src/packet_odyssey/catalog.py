from __future__ import annotations

from urllib.parse import SplitResult

from .models import (
    EventSeverity,
    FailureDefinition,
    FailureType,
    ScenarioDefinition,
    SimulationStage,
    SimulationStatus,
    StageDefinition,
    StageStatus,
)


def default_port(url: SplitResult) -> int:
    if url.port is not None:
        return url.port
    return 443 if url.scheme == "https" else 80


def path_and_query(url: SplitResult) -> str:
    path = url.path or "/"
    return f"{path}?{url.query}" if url.query else path


STAGE_ORDER: tuple[SimulationStage, ...] = (
    SimulationStage.BROWSER,
    SimulationStage.DNS,
    SimulationStage.TCP,
    SimulationStage.TLS,
    SimulationStage.FIREWALL,
    SimulationStage.LOAD_BALANCER,
    SimulationStage.API,
    SimulationStage.DATABASE,
)


STAGES: dict[SimulationStage, StageDefinition] = {
    SimulationStage.BROWSER: StageDefinition(
        SimulationStage.BROWSER,
        "Browser",
        "URL / HTTP",
        "The browser reads the URL and prepares an HTTP request.",
        "The browser parses scheme, hostname, port, path, and query before constructing request metadata.",
        180,
        lambda url: {"rawUrl": url.geturl()},
        lambda url: {
            "scheme": url.scheme,
            "hostname": url.hostname,
            "port": default_port(url),
            "path": path_and_query(url),
            "method": "GET",
            "headers": {"accept": "text/html", "user-agent": "PacketOdysseyCLI/0.1"},
        },
    ),
    SimulationStage.DNS: StageDefinition(
        SimulationStage.DNS,
        "Domain Name System",
        "DNS",
        "DNS translates the hostname into an IP address.",
        "The synthetic resolver models cache checks and an authoritative A-record response with a deterministic TTL.",
        260,
        lambda url: {"hostname": url.hostname, "recordType": "A"},
        lambda url: {
            "hostname": url.hostname,
            "resolvedAddress": "203.0.113.42",
            "recordType": "A",
            "ttlSeconds": 300,
            "resolver": "192.0.2.53",
        },
    ),
    SimulationStage.TCP: StageDefinition(
        SimulationStage.TCP,
        "TCP Connection",
        "TCP",
        "TCP opens a reliable connection to the destination server.",
        "The simulator models a three-way SYN, SYN-ACK, ACK handshake and records retransmission or refusal outcomes.",
        320,
        lambda url: {
            "sourceAddress": "198.51.100.24",
            "sourcePort": 51432,
            "destinationAddress": "203.0.113.42",
            "destinationPort": default_port(url),
        },
        lambda _url: {
            "handshake": ["SYN", "SYN-ACK", "ACK"],
            "connectionState": "ESTABLISHED",
            "roundTripMs": 42,
            "retransmissions": 0,
        },
    ),
    SimulationStage.TLS: StageDefinition(
        SimulationStage.TLS,
        "TLS Handshake",
        "TLS 1.3",
        "TLS verifies the server and creates an encrypted connection.",
        "The client and server negotiate TLS, validate the certificate, perform key exchange, and derive session keys.",
        360,
        lambda url: {
            "serverName": url.hostname,
            "supportedVersions": ["TLS 1.3", "TLS 1.2"],
            "cipherSuites": ["TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256"],
        },
        lambda url: {
            "negotiatedVersion": "TLS 1.3",
            "cipherSuite": "TLS_AES_256_GCM_SHA384",
            "certificateHostname": url.hostname,
            "certificateValid": True,
            "encrypted": True,
        },
    ),
    SimulationStage.FIREWALL: StageDefinition(
        SimulationStage.FIREWALL,
        "Firewall",
        "L3/L4 policy",
        "The firewall checks the request against network rules.",
        "The firewall evaluates source, destination, protocol, and port against an ordered rule set.",
        160,
        lambda url: {
            "sourceAddress": "198.51.100.24",
            "destinationAddress": "203.0.113.42",
            "protocol": "TCP",
            "destinationPort": default_port(url),
        },
        lambda url: {
            "decision": "ALLOW",
            "matchedRule": f"allow-tcp-{default_port(url)}",
            "inspectionTimeMs": 2,
        },
    ),
    SimulationStage.LOAD_BALANCER: StageDefinition(
        SimulationStage.LOAD_BALANCER,
        "Load Balancer",
        "HTTP routing",
        "The load balancer chooses a healthy application server.",
        "A round-robin policy selects one healthy backend and forwards the synthetic request.",
        210,
        lambda _url: {
            "algorithm": "round_robin",
            "backendPool": ["api-01", "api-02", "api-03"],
            "healthyBackends": ["api-01", "api-02"],
        },
        lambda _url: {
            "selectedBackend": "api-02",
            "backendAddress": "10.20.1.12:8080",
            "retries": 0,
        },
    ),
    SimulationStage.API: StageDefinition(
        SimulationStage.API,
        "Application API",
        "HTTP / JSON",
        "The API validates the request and runs application logic.",
        "The application matches a route, validates data, evaluates authorization, invokes logic, and prepares a response.",
        420,
        lambda url: {
            "method": "GET",
            "route": "/home" if (url.path or "/") == "/" else url.path,
            "traceId": "trace-odyssey-cli",
            "authenticated": False,
        },
        lambda _url: {
            "routeMatched": True,
            "statusCode": 200,
            "downstreamCall": "database.query",
            "responsePending": True,
        },
    ),
    SimulationStage.DATABASE: StageDefinition(
        SimulationStage.DATABASE,
        "Database",
        "PostgreSQL",
        "The database runs a query and returns data to the API.",
        "The simulator models pool acquisition, a parameterized indexed query, row retrieval, and response propagation.",
        380,
        lambda _url: {
            "pool": "primary-read-write",
            "query": "SELECT title, summary FROM pages WHERE slug = $1",
            "parameters": ["home"],
        },
        lambda _url: {
            "connectionAcquired": True,
            "indexUsed": "pages_slug_idx",
            "rowsReturned": 1,
            "transactionState": "COMMITTED",
            "finalHttpStatus": 200,
        },
    ),
}


def failure(
    type_: FailureType,
    title: str,
    stage: SimulationStage,
    severity: EventSeverity,
    blocking: bool,
    symptom: str,
    explanation: str,
    technical: str,
    troubleshooting: tuple[str, ...],
    event_type: str,
    event_message: str,
    output: dict[str, object],
    status: StageStatus,
    delay: int,
) -> FailureDefinition:
    return FailureDefinition(
        type_, title, stage, severity, blocking, symptom, explanation, technical,
        troubleshooting, event_type, event_message, output, status, delay
    )


FAILURES: dict[FailureType, FailureDefinition] = {
    FailureType.DNS_POISONING: failure(
        FailureType.DNS_POISONING, "DNS poisoning", SimulationStage.DNS,
        EventSeverity.WARNING, False,
        "The hostname resolves, but to an untrusted address.",
        "A manipulated DNS answer sends the request toward the wrong destination.",
        "The resolver returns an attacker-controlled A record. Transport can continue because name resolution technically succeeded.",
        ("Inspect DNS answers", "Compare trusted resolvers", "Validate DNSSEC where available"),
        "dns.poisoned_response", "DNS returned a suspicious address.",
        {"resolvedAddress": "198.51.100.66", "trusted": False, "ttlSeconds": 30},
        StageStatus.WARNING, 30,
    ),
    FailureType.DNS_TIMEOUT: failure(
        FailureType.DNS_TIMEOUT, "DNS timeout", SimulationStage.DNS,
        EventSeverity.ERROR, True,
        "The browser cannot resolve the hostname.",
        "The DNS resolver did not answer before the timeout budget expired.",
        "No usable DNS response arrived, so TCP cannot determine a destination address.",
        ("Check resolver reachability", "Inspect UDP/TCP port 53", "Retry with another resolver"),
        "dns.timeout", "DNS resolution exceeded the timeout budget.",
        {"responseReceived": False, "timeoutMs": 2000}, StageStatus.FAILED, 900,
    ),
    FailureType.PACKET_LOSS: failure(
        FailureType.PACKET_LOSS, "TCP packet loss", SimulationStage.TCP,
        EventSeverity.WARNING, False,
        "The connection succeeds after retransmission and extra latency.",
        "A handshake packet was lost and had to be retransmitted.",
        "The initial SYN-ACK is dropped; retransmission recovers the connection.",
        ("Inspect packet loss metrics", "Check network path quality", "Review retransmission counters"),
        "tcp.retransmission", "TCP recovered after retransmitting a lost packet.",
        {"connectionState": "ESTABLISHED", "retransmissions": 1, "roundTripMs": 168},
        StageStatus.WARNING, 520,
    ),
    FailureType.CONNECTION_REFUSED: failure(
        FailureType.CONNECTION_REFUSED, "Connection refused", SimulationStage.TCP,
        EventSeverity.ERROR, True,
        "The target actively rejects the TCP connection.",
        "No service is accepting connections on the destination port.",
        "The destination returns a TCP RST instead of completing the handshake.",
        ("Confirm the service is running", "Verify the destination port", "Inspect listener bindings"),
        "tcp.connection_refused", "The destination rejected the TCP connection.",
        {"connectionState": "REFUSED", "resetReceived": True}, StageStatus.FAILED, 80,
    ),
    FailureType.EXPIRED_CERTIFICATE: failure(
        FailureType.EXPIRED_CERTIFICATE, "Expired certificate", SimulationStage.TLS,
        EventSeverity.ERROR, True,
        "The browser blocks the HTTPS connection.",
        "The server certificate is outside its valid date range.",
        "Certificate validation fails because the notAfter timestamp is in the past.",
        ("Renew the certificate", "Verify deployment of the new chain", "Check system clock accuracy"),
        "tls.certificate_expired", "TLS certificate validation failed because the certificate expired.",
        {"certificateValid": False, "validationError": "CERT_HAS_EXPIRED", "encrypted": False},
        StageStatus.FAILED, 120,
    ),
    FailureType.HOSTNAME_MISMATCH: failure(
        FailureType.HOSTNAME_MISMATCH, "Certificate hostname mismatch", SimulationStage.TLS,
        EventSeverity.ERROR, True,
        "The browser reports that the certificate belongs to another host.",
        "The requested hostname is not covered by the certificate.",
        "SAN and common-name validation cannot match the requested SNI hostname.",
        ("Inspect certificate SAN entries", "Correct SNI routing", "Deploy the proper certificate"),
        "tls.hostname_mismatch", "The certificate does not match the requested hostname.",
        {"certificateValid": False, "validationError": "HOSTNAME_MISMATCH", "encrypted": False},
        StageStatus.FAILED, 110,
    ),
    FailureType.BLOCKED_PORT: failure(
        FailureType.BLOCKED_PORT, "Blocked firewall port", SimulationStage.FIREWALL,
        EventSeverity.ERROR, True,
        "Traffic is denied before it reaches the load balancer.",
        "A firewall rule blocks the destination port.",
        "The packet matches a deny rule for the TCP destination port.",
        ("Inspect firewall rule order", "Verify allowed ports", "Check network security groups"),
        "firewall.port_blocked", "The firewall denied traffic on the destination port.",
        {"decision": "DENY", "matchedRule": "deny-unapproved-ingress", "logged": True},
        StageStatus.FAILED, 20,
    ),
    FailureType.RATE_LIMITED: failure(
        FailureType.RATE_LIMITED, "Rate limit exceeded", SimulationStage.API,
        EventSeverity.ERROR, True,
        "The API returns HTTP 429.",
        "The request exceeds the allowed request rate.",
        "The rate limiter rejects the request before application business logic executes.",
        ("Inspect request volume", "Honor Retry-After", "Adjust client backoff or quotas"),
        "api.rate_limited", "The API rejected the request with HTTP 429.",
        {"statusCode": 429, "retryAfterSeconds": 30}, StageStatus.FAILED, 10,
    ),
    FailureType.NO_HEALTHY_BACKEND: failure(
        FailureType.NO_HEALTHY_BACKEND, "No healthy backend", SimulationStage.LOAD_BALANCER,
        EventSeverity.ERROR, True,
        "The load balancer returns service unavailable.",
        "Every application backend is failing health checks.",
        "The backend pool has zero eligible targets, so routing cannot continue.",
        ("Inspect health checks", "Verify backend readiness", "Review recent deployments"),
        "load_balancer.no_healthy_backend", "The load balancer found no healthy destination.",
        {"healthyBackends": [], "statusCode": 503, "selectedBackend": None},
        StageStatus.FAILED, 70,
    ),
    FailureType.API_TIMEOUT: failure(
        FailureType.API_TIMEOUT, "API timeout", SimulationStage.API,
        EventSeverity.ERROR, True,
        "The request exceeds the application time budget.",
        "The API does not finish its work before the timeout limit.",
        "Application processing exceeds the configured deadline and the request is cancelled.",
        ("Inspect slow spans", "Review downstream latency", "Set realistic deadlines and cancellation"),
        "api.timeout", "The API exceeded its request deadline.",
        {"statusCode": 504, "timeoutMs": 3000, "completed": False}, StageStatus.FAILED, 1000,
    ),
    FailureType.DATABASE_TIMEOUT: failure(
        FailureType.DATABASE_TIMEOUT, "Database timeout", SimulationStage.DATABASE,
        EventSeverity.ERROR, True,
        "The API cannot complete because the query times out.",
        "The database query exceeds the configured timeout.",
        "Query execution does not finish before statement_timeout and the transaction is aborted.",
        ("Inspect the query plan", "Check locks and load", "Add or correct indexes"),
        "database.timeout", "The database query exceeded its timeout.",
        {"completed": False, "timeoutMs": 1500, "transactionState": "ABORTED"},
        StageStatus.FAILED, 850,
    ),
    FailureType.DATABASE_UNAVAILABLE: failure(
        FailureType.DATABASE_UNAVAILABLE, "Database unavailable", SimulationStage.DATABASE,
        EventSeverity.ERROR, True,
        "The application cannot acquire a database connection.",
        "The database service is unreachable or offline.",
        "Connection establishment fails before query execution begins.",
        ("Check database health", "Inspect routing and credentials", "Verify failover state"),
        "database.unavailable", "The database could not accept a connection.",
        {"connectionAcquired": False, "completed": False}, StageStatus.FAILED, 400,
    ),
}


SCENARIOS: tuple[ScenarioDefinition, ...] = (
    ScenarioDefinition(
        "successful-https", "Successful HTTPS request",
        "A clean request completes across all eight stages.",
        "Understand the normal request path and the responsibility of each component.",
        "https://example.com/products?category=networking", None,
        SimulationStatus.COMPLETED, SimulationStage.DATABASE,
        "HTTP 200 response after a successful database query.",
    ),
    ScenarioDefinition(
        "dns-poisoning", "DNS poisoning",
        "DNS returns an untrusted address while transport still proceeds.",
        "Separate successful name resolution from trustworthy name resolution.",
        "https://bank.example/account", FailureType.DNS_POISONING,
        SimulationStatus.COMPLETED, SimulationStage.DATABASE,
        "A warning appears at DNS with an altered destination IP.",
    ),
    ScenarioDefinition(
        "tcp-packet-loss", "TCP packet loss",
        "A lost handshake packet triggers retransmission and added latency.",
        "Observe how TCP recovers from packet loss.",
        "https://media.example/video", FailureType.PACKET_LOSS,
        SimulationStatus.COMPLETED, SimulationStage.DATABASE,
        "The TCP stage completes with a warning and higher latency.",
    ),
    ScenarioDefinition(
        "expired-certificate", "Expired TLS certificate",
        "Certificate validation fails and downstream processing is skipped.",
        "Understand why HTTPS trust failures stop application traffic.",
        "https://legacy.example/login", FailureType.EXPIRED_CERTIFICATE,
        SimulationStatus.FAILED, SimulationStage.TLS,
        "The browser refuses the secure connection.",
    ),
    ScenarioDefinition(
        "firewall-blocked-port", "Firewall-blocked port",
        "A network policy denies the request before routing.",
        "See how network policy failures differ from application failures.",
        "https://internal.example/admin", FailureType.BLOCKED_PORT,
        SimulationStatus.FAILED, SimulationStage.FIREWALL,
        "The firewall denies the destination port.",
    ),
    ScenarioDefinition(
        "no-healthy-backend", "No healthy backend",
        "The load balancer has nowhere safe to route the request.",
        "Understand health checks and service availability.",
        "https://shop.example/checkout", FailureType.NO_HEALTHY_BACKEND,
        SimulationStatus.FAILED, SimulationStage.LOAD_BALANCER,
        "The load balancer returns HTTP 503.",
    ),
    ScenarioDefinition(
        "api-timeout", "API timeout",
        "Application processing exceeds the request deadline.",
        "Connect time budgets, cancellation, and gateway timeout symptoms.",
        "https://api.example/reports/annual", FailureType.API_TIMEOUT,
        SimulationStatus.FAILED, SimulationStage.API,
        "The API fails with a timeout before database execution.",
    ),
    ScenarioDefinition(
        "database-timeout", "Database timeout",
        "A slow query causes the final stage and request to fail.",
        "Trace a database problem back to the user-visible API failure.",
        "https://analytics.example/dashboard", FailureType.DATABASE_TIMEOUT,
        SimulationStatus.FAILED, SimulationStage.DATABASE,
        "The query is aborted after exceeding its statement timeout.",
    ),
)

SCENARIO_BY_ID = {scenario.id: scenario for scenario in SCENARIOS}
