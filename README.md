# Azure Migration Checklist

Azure migration readiness checklist and assessment script that flags blockers before you move.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Status: in development](https://img.shields.io/badge/status-in%20development-orange)

> **Status:** in active development. Star or watch the repo to follow progress. 

## Features

- Step-by-step migration checklist covering discovery, networking, identity, data, security and cutover
- Assessment script that scans an Azure subscription or on-prem inventory export and flags blockers
- Checks for unsupported OS versions, oversized VMs, public endpoints, missing tags and backup gaps
- Markdown and HTML readiness report you can share with stakeholders

## Tech stack

- Markdown checklist
- Python 3.11+
- Azure SDK for Python
- Azure CLI authentication

## Getting started

Setup instructions will be added with the first release.

## Roadmap

- [ ] Initial release
- [ ] Documentation and examples
- [ ] CI and automated tests

Have an idea? [Open an issue](https://github.com/calliarc/azure-migration-checklist/issues).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © 2026 CalliArc

---

Built and maintained by [CalliArc](https://www.calliarc.com/). Need help with Azure cloud migration? [Talk to our team](https://www.calliarc.com/services/azure-cloud-migration/).
