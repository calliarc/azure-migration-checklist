# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-09-23

First working release.

### Added

- Step-by-step migration checklist ([CHECKLIST.md](CHECKLIST.md)) covering discovery, identity, networking, data, security, governance/cost, cutover and post-migration
- Assessment CLI (`azmigrate-check`) that scans an on-prem inventory export (CSV/JSON) and/or a live Azure subscription and flags blockers
- Checks for unsupported/end-of-support OS versions, oversized VMs, disks over the managed disk limit, public endpoints, missing tags and backup gaps
- Markdown and self-contained HTML readiness report you can share with stakeholders
- CI-friendly exit codes (`--fail-on blocker|warning|info|never`) and a JSON rules config for thresholds, required tags, severities and OS lifecycle dates

[Unreleased]: https://github.com/calliarc/azure-migration-checklist/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/calliarc/azure-migration-checklist/releases/tag/v0.1.0
