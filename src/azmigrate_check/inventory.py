"""Load server inventories from CSV or JSON exports."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from azmigrate_check.models import Server

# Accepted column aliases -> canonical field name.
_ALIASES: dict[str, str] = {
    "name": "name",
    "hostname": "name",
    "server": "name",
    "vm_name": "name",
    "os": "os",
    "operating_system": "os",
    "os_name": "os",
    "version": "os_version",
    "os_version": "os_version",
    "cpu": "cpu",
    "cpus": "cpu",
    "vcpu": "cpu",
    "cores": "cpu",
    "ram": "ram_gb",
    "ram_gb": "ram_gb",
    "memory_gb": "ram_gb",
    "disk": "disk_gb",
    "disk_gb": "disk_gb",
    "storage_gb": "disk_gb",
    "public_ip": "public_ip",
    "tags": "tags",
    "backup": "backup",
    "backup_enabled": "backup",
    "environment": "environment",
    "env": "environment",
    "avg_cpu_percent": "avg_cpu_percent",
    "cpu_util": "avg_cpu_percent",
}

_TRUE = {"true", "yes", "y", "1", "enabled", "on"}
_FALSE = {"false", "no", "n", "0", "disabled", "off", "none"}


class InventoryError(ValueError):
    """Raised for malformed inventory input."""


def _parse_bool(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text == "" or text == "unknown":
        return None
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise InventoryError(f"Cannot interpret {value!r} as a boolean")


def _parse_number(value: Any, kind: type) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return kind(value)
    text = str(value).strip()
    if text == "":
        return None
    try:
        return kind(float(text))
    except ValueError as exc:
        raise InventoryError(f"Cannot interpret {value!r} as a number") from exc


def parse_tags(value: Any) -> dict[str, str]:
    """Parse tags from a dict or a ``key=value;key=value`` string."""
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(k).strip().lower(): str(v).strip() for k, v in value.items()}
    tags: dict[str, str] = {}
    for part in str(value).split(";"):
        part = part.strip()
        if not part:
            continue
        key, _, val = part.partition("=")
        tags[key.strip().lower()] = val.strip()
    return tags


def server_from_record(record: Mapping[str, Any], row: int | None = None) -> Server:
    fields: dict[str, Any] = {}
    for raw_key, value in record.items():
        if raw_key is None:
            continue
        canonical = _ALIASES.get(str(raw_key).strip().lower().replace(" ", "_"))
        if canonical:
            fields[canonical] = value

    where = f" (row {row})" if row is not None else ""
    name = str(fields.get("name") or "").strip()
    if not name:
        raise InventoryError(f"Server record is missing a name{where}")

    try:
        return Server(
            name=name,
            os=str(fields.get("os") or "").strip(),
            os_version=str(fields.get("os_version") or "").strip(),
            cpu=_parse_number(fields.get("cpu"), int),
            ram_gb=_parse_number(fields.get("ram_gb"), float),
            disk_gb=_parse_number(fields.get("disk_gb"), float),
            public_ip=str(fields.get("public_ip") or "").strip(),
            tags=parse_tags(fields.get("tags")),
            backup=_parse_bool(fields.get("backup")),
            environment=str(fields.get("environment") or "").strip(),
            avg_cpu_percent=_parse_number(fields.get("avg_cpu_percent"), float),
        )
    except InventoryError as exc:
        raise InventoryError(f"{exc} for server {name!r}{where}") from exc


def _from_records(records: Iterable[Mapping[str, Any]], row_offset: int) -> list[Server]:
    servers = [server_from_record(r, i + row_offset) for i, r in enumerate(records)]
    seen: set[str] = set()
    for s in servers:
        if s.name.lower() in seen:
            raise InventoryError(f"Duplicate server name {s.name!r}")
        seen.add(s.name.lower())
    return servers


def load_csv(path: str | Path) -> list[Server]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return _from_records(csv.DictReader(fh), row_offset=2)


def load_json(path: str | Path) -> list[Server]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("servers")
    if not isinstance(data, list):
        raise InventoryError("JSON inventory must be a list or an object with a 'servers' list")
    return _from_records(data, row_offset=1)


def load_inventory(path: str | Path) -> list[Server]:
    """Load an inventory file, choosing the parser by file extension."""
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return load_csv(path)
    if suffix == ".json":
        return load_json(path)
    raise InventoryError(f"Unsupported inventory format {suffix!r}; use .csv or .json")
