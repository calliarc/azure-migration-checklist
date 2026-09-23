import builtins
import json

from azmigrate_check.cli import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, main
from azmigrate_check.models import Assessment, Finding, Server, Severity
from azmigrate_check.report import to_html, to_markdown


def _assessment():
    srv = Server(name="web|<b>", os="Ubuntu", os_version="20.04", cpu=2, ram_gb=4)
    f = Finding("NET001", Severity.WARNING, srv.name, "Public <script>alert(1)</script>", "Fix")
    return Assessment(servers=[srv], findings=[f], as_of="2026-09-23")


def test_markdown_escapes_pipes():
    md = to_markdown(_assessment())
    assert "web\\|<b>" in md
    assert "| WARNING | NET001 |" in md


def test_html_escapes_content():
    out = to_html(_assessment())
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out
    assert out.startswith("<!DOCTYPE html>")


def test_empty_findings_message():
    a = Assessment(servers=[Server(name="x")], findings=[], as_of="2026-01-01")
    assert "No findings" in to_markdown(a)
    assert "No findings" in to_html(a)


def test_cli_writes_reports_and_fails_on_blocker(examples_dir, tmp_path, capsys):
    md, html = tmp_path / "r.md", tmp_path / "r.html"
    code = main(
        [
            str(examples_dir / "inventory.csv"),
            "--md",
            str(md),
            "--html",
            str(html),
            "--as-of",
            "2026-09-23",
        ]
    )
    assert code == EXIT_FINDINGS
    assert "db-legacy" in md.read_text()
    assert "<table>" in html.read_text()
    assert "blocker(s)" in capsys.readouterr().err


def test_cli_fail_on_never(examples_dir):
    assert main([str(examples_dir / "inventory.csv"), "--fail-on", "never", "-q"]) == EXIT_OK


def test_cli_clean_inventory_exits_zero(tmp_path, capsys):
    inv = tmp_path / "inv.json"
    inv.write_text(
        json.dumps(
            [
                {
                    "name": "ok",
                    "os": "Windows Server",
                    "version": "2022",
                    "tags": {"owner": "a", "environment": "dev", "cost-center": "c"},
                    "backup": True,
                }
            ]
        )
    )
    assert main([str(inv), "--as-of", "2026-09-23"]) == EXIT_OK
    assert "No findings" in capsys.readouterr().out


def test_cli_with_config(examples_dir):
    code = main(
        [
            str(examples_dir / "inventory.json"),
            "-c",
            str(examples_dir / "rules.json"),
            "-q",
            "--as-of",
            "2026-09-23",
        ]
    )
    assert code == EXIT_FINDINGS


def test_cli_errors(tmp_path, capsys):
    assert main([]) == EXIT_ERROR
    assert main([str(tmp_path / "missing.csv")]) == EXIT_ERROR
    bad = tmp_path / "bad.csv"
    bad.write_text("name,cpu\nsrv,many\n")
    assert main([str(bad)]) == EXIT_ERROR
    assert "error (inventory)" in capsys.readouterr().err


def test_cli_list_rules(capsys):
    assert main(["--list-rules"]) == EXIT_OK
    assert "OS001" in capsys.readouterr().out


def test_cli_subscription_without_sdk_degrades(monkeypatch, capsys):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("azure"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert main(["--subscription", "00000000-0000-0000-0000-000000000000"]) == EXIT_ERROR
    assert "Azure SDK not installed" in capsys.readouterr().err


def test_cli_subscription_env_missing(monkeypatch, capsys):
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    assert main(["--subscription", "env"]) == EXIT_ERROR
    assert "AZURE_SUBSCRIPTION_ID" in capsys.readouterr().err
