"""Assessment configuration (thresholds, required tags, rule overrides)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from azmigrate_check.lifecycle import LifecycleEntry, build_catalog
from azmigrate_check.models import Severity

# Largest single Azure managed disk size (32 TiB), in GiB.
AZURE_MAX_MANAGED_DISK_GB = 32767


@dataclass
class Config:
    required_tags: list[str] = field(
        default_factory=lambda: ["owner", "environment", "cost-center"]
    )
    eol_warning_days: int = 365
    max_vcpu: int = 64
    max_ram_gb: float = 512
    max_disk_gb: float = AZURE_MAX_MANAGED_DISK_GB
    underutilized_cpu_percent: float = 10.0
    production_environments: list[str] = field(default_factory=lambda: ["prod", "production"])
    severity_overrides: dict[str, Severity] = field(default_factory=dict)
    disabled_rules: list[str] = field(default_factory=list)
    os_lifecycle: dict[str, LifecycleEntry] = field(default_factory=build_catalog)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        known = {
            "required_tags",
            "eol_warning_days",
            "max_vcpu",
            "max_ram_gb",
            "max_disk_gb",
            "underutilized_cpu_percent",
            "production_environments",
            "severity_overrides",
            "disabled_rules",
            "os_lifecycle",
        }
        unknown = set(data) - known - {"$comment"}
        if unknown:
            raise ValueError(f"Unknown config key(s): {', '.join(sorted(unknown))}")

        cfg = cls()
        for key in ("eol_warning_days", "max_vcpu"):
            if key in data:
                setattr(cfg, key, int(data[key]))
        for key in ("max_ram_gb", "max_disk_gb", "underutilized_cpu_percent"):
            if key in data:
                setattr(cfg, key, float(data[key]))
        if "required_tags" in data:
            cfg.required_tags = [str(t).strip().lower() for t in data["required_tags"]]
        if "production_environments" in data:
            cfg.production_environments = [
                str(e).strip().lower() for e in data["production_environments"]
            ]
        if "disabled_rules" in data:
            cfg.disabled_rules = [str(r).upper() for r in data["disabled_rules"]]
        if "severity_overrides" in data:
            cfg.severity_overrides = {
                str(k).upper(): Severity(str(v).lower())
                for k, v in data["severity_overrides"].items()
            }
        if "os_lifecycle" in data:
            cfg.os_lifecycle = build_catalog(data["os_lifecycle"])
        return cfg

    @classmethod
    def load(cls, path: str | Path | None) -> Config:
        if path is None:
            return cls()
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("Config file must contain a JSON object")
        return cls.from_dict(data)
