from datetime import date

import pytest

from azmigrate_check.config import Config
from azmigrate_check.models import Server, Severity
from azmigrate_check.rules import assess

AS_OF = date(2026, 9, 23)
TAGS = {"owner": "a", "environment": "dev", "cost-center": "c"}


def clean_server(**overrides) -> Server:
    base = dict(
        name="srv",
        os="Windows Server",
        os_version="2022",
        cpu=4,
        ram_gb=16,
        disk_gb=256,
        tags=dict(TAGS),
        backup=True,
    )
    base.update(overrides)
    return Server(**base)


def findings(server, cfg=None):
    return assess([server], cfg or Config(), AS_OF).findings


def by_rule(server, rule_id, cfg=None):
    return [f for f in findings(server, cfg) if f.rule_id == rule_id]


def test_clean_server_has_no_findings():
    assert findings(clean_server()) == []


def test_eol_os_is_blocker():
    (f,) = by_rule(clean_server(os_version="2012 R2"), "OS001")
    assert f.severity is Severity.BLOCKER
    assert "2023-10-10" in f.message


def test_os_near_eol_is_warning():
    (f,) = by_rule(clean_server(os_version="2016"), "OS001")
    assert f.severity is Severity.WARNING


def test_eol_warning_window_is_configurable():
    cfg = Config.from_dict({"eol_warning_days": 30})
    assert by_rule(clean_server(os_version="2016"), "OS001", cfg) == []


def test_unknown_os_is_info():
    (f,) = by_rule(clean_server(os="FreeBSD", os_version="13"), "OS001")
    assert f.severity is Severity.INFO


def test_oversized_vm():
    (f,) = by_rule(clean_server(cpu=128, ram_gb=1024), "VM001")
    assert f.severity is Severity.WARNING
    assert "128 vCPU" in f.message and "1024 GB" in f.message


def test_underutilized_vm_is_info():
    (f,) = by_rule(clean_server(cpu=8, avg_cpu_percent=3), "VM002")
    assert f.severity is Severity.INFO


def test_disk_over_managed_disk_limit():
    (f,) = by_rule(clean_server(disk_gb=40000), "DSK001")
    assert f.severity is Severity.WARNING


def test_public_ip_flagged():
    (f,) = by_rule(clean_server(public_ip="203.0.113.1"), "NET001")
    assert "203.0.113.1" in f.message


def test_missing_tags():
    (f,) = by_rule(clean_server(tags={"owner": "a"}), "TAG001")
    assert "environment" in f.message and "cost-center" in f.message


def test_environment_field_satisfies_environment_tag():
    srv = clean_server(tags={"owner": "a", "cost-center": "c"}, environment="dev")
    assert by_rule(srv, "TAG001") == []


@pytest.mark.parametrize(
    ("env", "severity"), [("prod", Severity.BLOCKER), ("dev", Severity.WARNING)]
)
def test_no_backup_severity_depends_on_environment(env, severity):
    srv = clean_server(backup=False, tags={**TAGS, "environment": env})
    (f,) = by_rule(srv, "BAK001")
    assert f.severity is severity


def test_unknown_backup_is_info():
    (f,) = by_rule(clean_server(backup=None), "BAK001")
    assert f.severity is Severity.INFO


def test_severity_override_and_disabled_rules():
    srv = clean_server(public_ip="203.0.113.1", tags={})
    cfg = Config.from_dict(
        {"severity_overrides": {"net001": "blocker"}, "disabled_rules": ["TAG001"]}
    )
    result = findings(srv, cfg)
    assert [f.rule_id for f in result] == ["NET001"]
    assert result[0].severity is Severity.BLOCKER


def test_unknown_config_key_rejected():
    with pytest.raises(ValueError):
        Config.from_dict({"max_cpus": 4})


def test_server_status_and_sorting():
    servers = [
        clean_server(name="a"),
        clean_server(name="b", public_ip="203.0.113.1"),
        clean_server(name="c", os_version="2008 R2"),
    ]
    a = assess(servers, Config(), AS_OF)
    assert [a.server_status(n) for n in "abc"] == ["ready", "review", "blocked"]
    assert a.findings[0].severity is Severity.BLOCKER
