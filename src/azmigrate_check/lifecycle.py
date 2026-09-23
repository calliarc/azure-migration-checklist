"""Operating system lifecycle (end-of-support) catalog.

The dates below are the vendor end-of-support dates as publicly documented at the
time of writing (Microsoft Lifecycle, Canonical, Red Hat, SUSE, Debian LTS). They
are provided as defaults for convenience only. Vendor dates can change, and paid
extended-support programmes (for example Microsoft ESU, Ubuntu Pro/ESM, RHEL ELS)
can extend coverage. ALWAYS verify against the vendor's lifecycle page and override
entries via the ``os_lifecycle`` key of a rules config file when needed.

Keys are ``"<family>:<version>"``. Dates are ISO ``YYYY-MM-DD``. Entries marked
``approximate date`` are month-level; the first day of the month is used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LifecycleEntry:
    family: str
    version: str
    end_of_support: date
    label: str
    note: str = ""


# (key, end-of-support, display label, note)
_DEFAULTS: list[tuple[str, str, str, str]] = [
    # Microsoft Windows Server - end of extended support
    ("windows-server:2003", "2015-07-14", "Windows Server 2003", ""),
    ("windows-server:2008", "2020-01-14", "Windows Server 2008", ""),
    ("windows-server:2008 r2", "2020-01-14", "Windows Server 2008 R2", ""),
    ("windows-server:2012", "2023-10-10", "Windows Server 2012", "ESU may apply"),
    ("windows-server:2012 r2", "2023-10-10", "Windows Server 2012 R2", "ESU may apply"),
    ("windows-server:2016", "2027-01-12", "Windows Server 2016", ""),
    ("windows-server:2019", "2029-01-09", "Windows Server 2019", ""),
    ("windows-server:2022", "2031-10-14", "Windows Server 2022", ""),
    ("windows-server:2025", "2034-11-14", "Windows Server 2025", ""),
    # Ubuntu LTS - end of standard support (Ubuntu Pro/ESM extends this)
    ("ubuntu:14.04", "2019-04-30", "Ubuntu 14.04 LTS", ""),
    ("ubuntu:16.04", "2021-04-30", "Ubuntu 16.04 LTS", ""),
    ("ubuntu:18.04", "2023-05-31", "Ubuntu 18.04 LTS", ""),
    ("ubuntu:20.04", "2025-05-31", "Ubuntu 20.04 LTS", ""),
    ("ubuntu:22.04", "2027-04-01", "Ubuntu 22.04 LTS", "approximate date"),
    ("ubuntu:24.04", "2029-04-01", "Ubuntu 24.04 LTS", "approximate date"),
    # Red Hat Enterprise Linux - end of maintenance support
    ("rhel:6", "2020-11-30", "RHEL 6", ""),
    ("rhel:7", "2024-06-30", "RHEL 7", "ELS may apply"),
    ("rhel:8", "2029-05-31", "RHEL 8", ""),
    ("rhel:9", "2032-05-31", "RHEL 9", ""),
    # CentOS Linux (discontinued)
    ("centos:6", "2020-11-30", "CentOS 6", ""),
    ("centos:7", "2024-06-30", "CentOS 7", ""),
    ("centos:8", "2021-12-31", "CentOS 8", ""),
    # SUSE Linux Enterprise Server - end of general support (latest SP)
    ("sles:11", "2019-03-31", "SLES 11", ""),
    ("sles:12", "2024-10-31", "SLES 12", "LTSS may apply"),
    ("sles:15", "2031-07-31", "SLES 15", ""),
    # Debian - end of LTS
    ("debian:9", "2022-06-30", "Debian 9", ""),
    ("debian:10", "2024-06-30", "Debian 10", ""),
    ("debian:11", "2026-08-31", "Debian 11", ""),
    ("debian:12", "2028-06-30", "Debian 12", ""),
]


def default_catalog() -> dict[str, LifecycleEntry]:
    catalog: dict[str, LifecycleEntry] = {}
    for key, eos, label, note in _DEFAULTS:
        family, version = key.split(":", 1)
        catalog[key] = LifecycleEntry(family, version, date.fromisoformat(eos), label, note)
    return catalog


def build_catalog(overrides: dict[str, str] | None = None) -> dict[str, LifecycleEntry]:
    """Return the default catalog with ``overrides`` (key -> ISO date) applied."""
    catalog = default_catalog()
    for key, value in (overrides or {}).items():
        key = key.strip().lower()
        if ":" not in key:
            raise ValueError(f"os_lifecycle key must look like 'family:version', got {key!r}")
        family, version = key.split(":", 1)
        existing = catalog.get(key)
        label = existing.label if existing else f"{family} {version}"
        catalog[key] = LifecycleEntry(
            family, version, date.fromisoformat(value), label, "overridden in config"
        )
    return catalog


_FAMILY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("windows-server", re.compile(r"windows")),
    ("ubuntu", re.compile(r"ubuntu")),
    ("rhel", re.compile(r"\brhel\b|red\s*hat")),
    ("centos", re.compile(r"centos")),
    ("sles", re.compile(r"\bsles\b|suse")),
    ("debian", re.compile(r"debian")),
]


def normalize_os(os_name: str, version: str = "") -> tuple[str, str] | None:
    """Map free-text OS name/version to a ``(family, version)`` catalog key.

    Returns ``None`` if the OS family is not recognised.
    """
    text = f"{os_name} {version}".lower()
    family = next((fam for fam, pat in _FAMILY_PATTERNS if pat.search(text)), None)
    if family is None:
        return None

    if family == "windows-server":
        m = re.search(r"(2003|2008|2012|2016|2019|2022|2025)(\s*r2)?", text)
        if not m:
            return family, ""
        return family, m.group(1) + (" r2" if m.group(2) else "")

    if family == "ubuntu":
        m = re.search(r"(\d{2})\.(\d{2})", text)
        return family, f"{m.group(1)}.{m.group(2)}" if m else ""

    # rhel / centos / sles / debian: major version is what matters
    m = re.search(r"(?<![\d.])(\d{1,2})(?:[.\s]|sp|$)", version.lower()) or re.search(
        r"(?<![\d.])(\d{1,2})(?:[.\s]|sp|$)", text
    )
    return family, m.group(1) if m else ""


def lookup(
    catalog: dict[str, LifecycleEntry], os_name: str, version: str = ""
) -> tuple[tuple[str, str] | None, LifecycleEntry | None]:
    """Return the normalized key and matching catalog entry (if any)."""
    key = normalize_os(os_name, version)
    if key is None:
        return None, None
    return key, catalog.get(f"{key[0]}:{key[1]}")
