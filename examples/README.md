# Examples

All files in this folder are **sample data**: fictional server names and IP addresses from
the RFC 5737 documentation ranges (`198.51.100.0/24`, `203.0.113.0/24`). They are not real
systems or customer data.

| File | Purpose |
|---|---|
| `inventory.csv` | Sample CSV inventory export (tags as `key=value;key=value`) |
| `inventory.json` | Sample JSON inventory (tags as an object) |
| `rules.json` | Example rules config showing every supported key |

```bash
azmigrate-check examples/inventory.csv --md report.md --html report.html
azmigrate-check examples/inventory.json -c examples/rules.json --fail-on warning
```
