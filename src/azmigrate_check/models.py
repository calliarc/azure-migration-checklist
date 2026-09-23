"""Core data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Finding severity, ordered from least to most serious."""

    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"

    @property
    def rank(self) -> int:
        return {"info": 0, "warning": 1, "blocker": 2}[self.value]


@dataclass
class Server:
    """A single server/VM from an inventory export or a live subscription."""

    name: str
    os: str = ""
    os_version: str = ""
    cpu: int | None = None
    ram_gb: float | None = None
    disk_gb: float | None = None
    public_ip: str = ""
    tags: dict[str, str] = field(default_factory=dict)
    backup: bool | None = None  # None = unknown
    environment: str = ""
    avg_cpu_percent: float | None = None
    source: str = "inventory"


@dataclass(frozen=True)
class Finding:
    """A single issue raised by a rule against a server."""

    rule_id: str
    severity: Severity
    server: str
    message: str
    remediation: str = ""


@dataclass
class Assessment:
    """Result of running all rules against an inventory."""

    servers: list[Server]
    findings: list[Finding]
    as_of: str

    def count(self, severity: Severity) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    def findings_for(self, server_name: str) -> list[Finding]:
        return [f for f in self.findings if f.server == server_name]

    def server_status(self, server_name: str) -> str:
        """Return 'blocked', 'review' or 'ready' for a server."""
        sevs = {f.severity for f in self.findings_for(server_name)}
        if Severity.BLOCKER in sevs:
            return "blocked"
        if Severity.WARNING in sevs:
            return "review"
        return "ready"

    def max_severity(self) -> Severity | None:
        if not self.findings:
            return None
        return max((f.severity for f in self.findings), key=lambda s: s.rank)
