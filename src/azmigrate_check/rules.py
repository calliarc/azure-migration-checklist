"""Readiness rules. Each rule inspects one server and yields findings."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date

from azmigrate_check.config import Config
from azmigrate_check.lifecycle import lookup
from azmigrate_check.models import Assessment, Finding, Server, Severity

RuleFunc = Callable[[Server, Config, date], Iterator[Finding]]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    func: RuleFunc


def _env(server: Server) -> str:
    return (
        server.environment or server.tags.get("environment") or server.tags.get("env") or ""
    ).lower()


def check_os_support(server: Server, cfg: Config, as_of: date) -> Iterator[Finding]:
    if not server.os:
        yield Finding(
            "OS001",
            Severity.INFO,
            server.name,
            "Operating system not recorded.",
            "Capture the OS and version so support status can be verified.",
        )
        return
    key, entry = lookup(cfg.os_lifecycle, server.os, server.os_version)
    os_text = f"{server.os} {server.os_version}".strip()
    if entry is None:
        yield Finding(
            "OS001",
            Severity.INFO,
            server.name,
            f"OS '{os_text}' is not in the lifecycle catalog; support status unknown.",
            "Verify vendor support and Azure endorsement manually, or add it to "
            "'os_lifecycle' in the rules config.",
        )
        return
    days_left = (entry.end_of_support - as_of).days
    eos = entry.end_of_support.isoformat()
    extra = f" ({entry.note})" if entry.note else ""
    if days_left < 0:
        yield Finding(
            "OS001",
            Severity.BLOCKER,
            server.name,
            f"{entry.label} reached end of support on {eos}{extra}.",
            "Upgrade the OS before or during migration, or confirm eligibility for a paid "
            "extended-support programme (some are available at no extra cost on Azure).",
        )
    elif days_left <= cfg.eol_warning_days:
        yield Finding(
            "OS001",
            Severity.WARNING,
            server.name,
            f"{entry.label} reaches end of support on {eos} ({days_left} days){extra}.",
            "Plan an OS upgrade as part of the migration wave.",
        )


def check_vm_size(server: Server, cfg: Config, as_of: date) -> Iterator[Finding]:
    reasons = []
    if server.cpu is not None and server.cpu > cfg.max_vcpu:
        reasons.append(f"{server.cpu} vCPU > {cfg.max_vcpu}")
    if server.ram_gb is not None and server.ram_gb > cfg.max_ram_gb:
        reasons.append(f"{server.ram_gb:g} GB RAM > {cfg.max_ram_gb:g} GB")
    if reasons:
        yield Finding(
            "VM001",
            Severity.WARNING,
            server.name,
            "Oversized VM: " + "; ".join(reasons) + ".",
            "Validate sizing with performance data; large SKUs are costly and have limited "
            "regional availability and quota.",
        )
    if (
        server.avg_cpu_percent is not None
        and server.cpu is not None
        and server.cpu > 2
        and server.avg_cpu_percent < cfg.underutilized_cpu_percent
    ):
        yield Finding(
            "VM002",
            Severity.INFO,
            server.name,
            f"Average CPU {server.avg_cpu_percent:g}% on {server.cpu} vCPU; "
            "likely overprovisioned.",
            "Right-size to a smaller SKU instead of lifting-and-shifting the current size.",
        )


def check_disk(server: Server, cfg: Config, as_of: date) -> Iterator[Finding]:
    if server.disk_gb is not None and server.disk_gb > cfg.max_disk_gb:
        yield Finding(
            "DSK001",
            Severity.WARNING,
            server.name,
            f"Disk of {server.disk_gb:g} GB exceeds {cfg.max_disk_gb:g} GB "
            "(largest single managed disk).",
            "Split data across multiple managed disks (e.g. striped volumes) or move bulk "
            "data to Azure Files / Blob Storage.",
        )


def check_public_endpoint(server: Server, cfg: Config, as_of: date) -> Iterator[Finding]:
    if server.public_ip:
        yield Finding(
            "NET001",
            Severity.WARNING,
            server.name,
            f"Server is exposed on a public IP ({server.public_ip}).",
            "Put it behind Azure Bastion, a load balancer/Application Gateway with WAF, or "
            "a private endpoint; restrict with NSGs.",
        )


def check_tags(server: Server, cfg: Config, as_of: date) -> Iterator[Finding]:
    present = {k for k, v in server.tags.items() if v}
    if server.environment:
        present.add("environment")
    missing = [t for t in cfg.required_tags if t not in present]
    if missing:
        yield Finding(
            "TAG001",
            Severity.WARNING,
            server.name,
            "Missing required tag(s): " + ", ".join(missing) + ".",
            "Add the tags in the inventory and enforce them in Azure with Azure Policy.",
        )


def check_backup(server: Server, cfg: Config, as_of: date) -> Iterator[Finding]:
    if server.backup is None:
        yield Finding(
            "BAK001",
            Severity.INFO,
            server.name,
            "Backup status unknown.",
            "Confirm backup coverage and plan Azure Backup protection after migration.",
        )
    elif server.backup is False:
        is_prod = _env(server) in cfg.production_environments
        yield Finding(
            "BAK001",
            Severity.BLOCKER if is_prod else Severity.WARNING,
            server.name,
            "No backup configured" + (" on a production server." if is_prod else "."),
            "Take a verified backup before cutover and enable Azure Backup on the target VM.",
        )


RULES: list[Rule] = [
    Rule("OS001", "Unsupported / end-of-support operating system", check_os_support),
    Rule("VM001", "Oversized VM", check_vm_size),
    Rule("DSK001", "Disk exceeds managed disk limit", check_disk),
    Rule("NET001", "Public endpoint", check_public_endpoint),
    Rule("TAG001", "Missing required tags", check_tags),
    Rule("BAK001", "Backup gap", check_backup),
]


def assess(
    servers: list[Server], cfg: Config | None = None, as_of: date | None = None
) -> Assessment:
    """Run every enabled rule against every server."""
    cfg = cfg or Config()
    as_of = as_of or date.today()
    disabled = set(cfg.disabled_rules)
    findings: list[Finding] = []
    for server in servers:
        for rule in RULES:
            if rule.rule_id in disabled:
                continue
            for f in rule.func(server, cfg, as_of):
                if f.rule_id in disabled:
                    continue
                override = cfg.severity_overrides.get(f.rule_id)
                if override is not None:
                    f = Finding(f.rule_id, override, f.server, f.message, f.remediation)
                findings.append(f)
    findings.sort(key=lambda f: (-f.severity.rank, f.server.lower(), f.rule_id))
    return Assessment(servers=servers, findings=findings, as_of=as_of.isoformat())
