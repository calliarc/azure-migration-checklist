"""Command-line interface for azmigrate-check."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from azmigrate_check import __version__
from azmigrate_check.config import Config
from azmigrate_check.inventory import InventoryError, load_inventory
from azmigrate_check.models import Server, Severity
from azmigrate_check.report import to_html, to_markdown
from azmigrate_check.rules import RULES, assess

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

_FAIL_ON = {"blocker": 2, "warning": 1, "info": 0, "never": 99}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="azmigrate-check",
        description="Assess Azure migration readiness of a server inventory or live subscription.",
    )
    p.add_argument(
        "inventory", nargs="*", type=Path, help="Inventory export(s) in CSV or JSON format."
    )
    p.add_argument(
        "--subscription",
        metavar="ID",
        help="Also scan VMs in this Azure subscription (requires the 'azure' extra). "
        "Use --subscription env to read AZURE_SUBSCRIPTION_ID.",
    )
    p.add_argument("-c", "--config", type=Path, help="Rules config file (JSON).")
    p.add_argument("--md", "--markdown", dest="md", type=Path, help="Write Markdown report here.")
    p.add_argument("--html", type=Path, help="Write HTML report here.")
    p.add_argument("--title", default="Azure Migration Readiness Report", help="Report title.")
    p.add_argument(
        "--fail-on",
        choices=list(_FAIL_ON),
        default="blocker",
        help="Exit 1 if any finding at or above this severity (default: blocker).",
    )
    p.add_argument(
        "--as-of",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Evaluate end-of-support dates as of this date (default: today).",
    )
    p.add_argument("--list-rules", action="store_true", help="List available rules and exit.")
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress the summary on stderr.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        for rule in RULES:
            print(f"{rule.rule_id:<8} {rule.title}")
        return EXIT_OK

    if not args.inventory and not args.subscription:
        parser.print_usage(sys.stderr)
        print("error: provide an inventory file and/or --subscription", file=sys.stderr)
        return EXIT_ERROR

    try:
        cfg = Config.load(args.config)
        servers: list[Server] = []
        for path in args.inventory:
            servers.extend(load_inventory(path))
        if args.subscription:
            from azmigrate_check.azure_live import AzureUnavailableError, load_from_subscription

            sub = None if args.subscription == "env" else args.subscription
            try:
                servers.extend(load_from_subscription(sub))
            except AzureUnavailableError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return EXIT_ERROR
    except (OSError, ValueError) as exc:  # InventoryError is a ValueError
        kind = "inventory" if isinstance(exc, InventoryError) else "input"
        print(f"error ({kind}): {exc}", file=sys.stderr)
        return EXIT_ERROR

    assessment = assess(servers, cfg, args.as_of)

    markdown = to_markdown(assessment, args.title)
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(markdown, encoding="utf-8")
    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(to_html(assessment, args.title), encoding="utf-8")
    if not args.md and not args.html:
        print(markdown)

    if not args.quiet:
        print(
            f"azmigrate-check: {len(servers)} server(s), "
            f"{assessment.count(Severity.BLOCKER)} blocker(s), "
            f"{assessment.count(Severity.WARNING)} warning(s), "
            f"{assessment.count(Severity.INFO)} info",
            file=sys.stderr,
        )

    worst = assessment.max_severity()
    if worst is not None and worst.rank >= _FAIL_ON[args.fail_on]:
        return EXIT_FINDINGS
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
