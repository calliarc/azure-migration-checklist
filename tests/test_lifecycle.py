from datetime import date

import pytest

from azmigrate_check.lifecycle import build_catalog, lookup, normalize_os


@pytest.mark.parametrize(
    ("os_name", "version", "expected"),
    [
        ("Windows Server", "2012 R2", ("windows-server", "2012 r2")),
        ("Microsoft Windows Server 2019 Datacenter", "", ("windows-server", "2019")),
        ("Windows Server", "2008", ("windows-server", "2008")),
        ("Ubuntu", "22.04.4 LTS", ("ubuntu", "22.04")),
        ("Red Hat Enterprise Linux", "7.9", ("rhel", "7")),
        ("RHEL", "9", ("rhel", "9")),
        ("CentOS Linux", "7.9.2009", ("centos", "7")),
        ("SUSE Linux Enterprise Server", "12 SP5", ("sles", "12")),
        ("Debian GNU/Linux", "11", ("debian", "11")),
    ],
)
def test_normalize_os(os_name, version, expected):
    assert normalize_os(os_name, version) == expected


def test_unknown_family_returns_none():
    assert normalize_os("FreeBSD", "13") is None


def test_lookup_hits_catalog():
    catalog = build_catalog()
    _, entry = lookup(catalog, "Windows Server", "2012 R2")
    assert entry is not None
    assert entry.end_of_support == date(2023, 10, 10)


def test_overrides_replace_and_add_entries():
    catalog = build_catalog({"ubuntu:22.04": "2027-06-30", "rocky:9": "2032-05-31"})
    assert catalog["ubuntu:22.04"].end_of_support == date(2027, 6, 30)
    assert catalog["rocky:9"].end_of_support == date(2032, 5, 31)


def test_override_key_must_have_family():
    with pytest.raises(ValueError):
        build_catalog({"ubuntu": "2030-01-01"})
