# Azure Migration Checklist

Azure migration readiness checklist and assessment script that flags blockers before you move.

[![CI](https://github.com/calliarc/azure-migration-checklist/actions/workflows/ci.yml/badge.svg)](https://github.com/calliarc/azure-migration-checklist/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/calliarc/azure-migration-checklist?include_prereleases&sort=semver)](https://github.com/calliarc/azure-migration-checklist/releases)
[![Built by CalliArc](https://img.shields.io/badge/built%20by-CalliArc-0a66c2)](https://www.calliarc.com/)

> **Status:** v0.1.0, the first working release. The checklist and the offline inventory assessment are stable; live subscription scanning is new and read-only. Feedback and issues are welcome.

## Features

- Step-by-step migration checklist ([CHECKLIST.md](CHECKLIST.md)) covering discovery, identity, networking, data, security, governance/cost, cutover and post-migration
- Assessment CLI (`azmigrate-check`) that scans an on-prem inventory export (CSV/JSON) and/or a live Azure subscription and flags blockers
- Checks for unsupported/end-of-support OS versions, oversized VMs, disks over the managed disk limit, public endpoints, missing tags and backup gaps
- Markdown and self-contained HTML readiness report you can share with stakeholders
- CI-friendly exit codes (`--fail-on blocker|warning|info|never`) and a JSON rules config for thresholds, required tags, severities and OS lifecycle dates

## Tech stack

- Markdown checklist
- Python 3.10+ (no runtime dependencies for inventory assessment)
- Azure SDK for Python (`azure-identity`, `azure-mgmt-compute`, `azure-mgmt-network`), optional
- Azure CLI authentication (via `DefaultAzureCredential`)

## Getting started

### Install

```bash
git clone https://github.com/calliarc/azure-migration-checklist.git
cd azure-migration-checklist
python -m venv .venv && source .venv/bin/activate

pip install .              # inventory assessment only
pip install ".[azure]"     # add live subscription scanning
```

### Assess an inventory export

```bash
azmigrate-check examples/inventory.csv --md report.md --html report.html
```

Without `--md`/`--html`, the Markdown report is printed to stdout. A one-line summary goes to stderr.

Inventory columns (CSV header or JSON keys; common aliases like `hostname`, `vcpu`, `memory_gb` are accepted):

| Column | Example | Notes |
|---|---|---|
| `name` | `web-01` | Required, unique |
| `os`, `version` | `Windows Server`, `2012 R2` | Used for end-of-support checks |
| `cpu`, `ram_gb`, `disk_gb` | `8`, `32`, `512` | `disk_gb` is the largest single disk |
| `public_ip` | `203.0.113.10` | Any value flags a public endpoint |
| `tags` | `owner=web;cost-center=CC1` | JSON may use an object |
| `backup` | `yes` / `no` / `unknown` | |
| `environment` | `prod` | Also read from the `environment`/`env` tag |
| `avg_cpu_percent` | `6` | Optional; used for right-sizing hints |

See [examples/](examples/) for sample (fictional) CSV and JSON inventories.

### Scan a live subscription (optional)

```bash
az login
azmigrate-check --subscription <subscription-id> --html azure-report.html
# or: export AZURE_SUBSCRIPTION_ID=...; azmigrate-check --subscription env
```

Access is read-only and needs the **Reader** role. Credentials are resolved by `DefaultAzureCredential` (Azure CLI, environment variables, managed identity); see [.env.example](.env.example). If the SDK is not installed or authentication fails, the tool exits with code 2 and a clear message. Backup status is not read from Recovery Services vaults yet, so live VMs report backup as *unknown*. You can combine inventory files and `--subscription` in one run.

### Rules

| Rule | Checks | Default severity |
|---|---|---|
| `OS001` | OS past end of support / within `eol_warning_days` / not in catalog | blocker / warning / info |
| `VM001` | vCPU > `max_vcpu` (64) or RAM > `max_ram_gb` (512) | warning |
| `VM002` | Average CPU < `underutilized_cpu_percent` (10%) | info |
| `DSK001` | Disk > `max_disk_gb` (32,767 GiB, the largest managed disk) | warning |
| `NET001` | Public IP assigned | warning |
| `TAG001` | Missing `required_tags` (`owner`, `environment`, `cost-center`) | warning |
| `BAK001` | No backup (blocker on production) / backup unknown | blocker or warning / info |

Customise any of these with `-c rules.json` (see [examples/rules.json](examples/rules.json)): thresholds, required tags, production environment names, `severity_overrides`, `disabled_rules` and `os_lifecycle` date overrides.

> **About OS end-of-support dates:** the built-in catalog uses vendor end-of-support dates (Microsoft, Canonical, Red Hat, SUSE, Debian) as documented at the time of release. Some Ubuntu dates are month-level approximations and are marked as such. Paid or Azure-included extended-support programmes (ESU, Ubuntu Pro, RHEL ELS, SUSE LTSS) are not modelled. Verify dates against vendor lifecycle pages and override them in `os_lifecycle` when needed. Use `--as-of YYYY-MM-DD` for reproducible reports.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | No findings at or above `--fail-on` (default `blocker`) |
| `1` | At least one finding at or above `--fail-on` |
| `2` | Usage, input or Azure connection error |

### Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

Tests run fully offline and do not need an Azure account.

## Roadmap

- [x] Initial release
- [x] Documentation and examples
- [x] CI and automated tests
- [ ] Read backup status from Recovery Services vaults in live scans
- [ ] Database and PaaS readiness checks
- [ ] Azure Migrate export import

Have an idea? [Open an issue](https://github.com/calliarc/azure-migration-checklist/issues).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE) © 2026 CalliArc

---

Built and maintained by [CalliArc](https://www.calliarc.com/). Need help with Azure cloud migration? [Talk to our team](https://www.calliarc.com/services/azure-cloud-migration/).
