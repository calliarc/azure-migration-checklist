import json

import pytest

from azmigrate_check.inventory import InventoryError, load_inventory, parse_tags


def test_load_sample_csv(examples_dir):
    servers = load_inventory(examples_dir / "inventory.csv")
    assert len(servers) == 8
    web02 = next(s for s in servers if s.name == "web-02")
    assert web02.cpu == 4 and web02.ram_gb == 16.0
    assert web02.public_ip == "203.0.113.10"
    assert web02.tags == {"owner": "web-team", "cost-center": "CC100"}
    assert web02.backup is True
    file01 = next(s for s in servers if s.name == "file-01")
    assert file01.backup is None
    assert file01.avg_cpu_percent is None


def test_load_sample_json(examples_dir):
    servers = load_inventory(examples_dir / "inventory.json")
    assert [s.name for s in servers] == ["jump-01", "build-01", "erp-01", "legacy-ftp"]
    assert servers[0].tags["environment"] == "prod"


def test_column_aliases(tmp_path):
    p = tmp_path / "inv.csv"
    p.write_text("Hostname,Operating System,OS Version,vCPU,Memory GB\nsrv,Ubuntu,24.04,2,4\n")
    (srv,) = load_inventory(p)
    assert (srv.name, srv.os, srv.os_version, srv.cpu, srv.ram_gb) == (
        "srv",
        "Ubuntu",
        "24.04",
        2,
        4,
    )


def test_parse_tags_string_and_dict():
    assert parse_tags("Owner=a; env = prod;;") == {"owner": "a", "env": "prod"}
    assert parse_tags({"Owner": "a"}) == {"owner": "a"}
    assert parse_tags(None) == {}


@pytest.mark.parametrize(
    "content",
    [
        "name,cpu\n,4\n",  # missing name
        "name,cpu\nsrv,lots\n",  # bad number
        "name,backup\nsrv,maybe\n",  # bad boolean
        "name\nsrv\nSRV\n",  # duplicate
    ],
)
def test_bad_csv_raises(tmp_path, content):
    p = tmp_path / "inv.csv"
    p.write_text(content)
    with pytest.raises(InventoryError):
        load_inventory(p)


def test_bad_json_shape(tmp_path):
    p = tmp_path / "inv.json"
    p.write_text(json.dumps({"hosts": []}))
    with pytest.raises(InventoryError):
        load_inventory(p)


def test_unsupported_extension(tmp_path):
    p = tmp_path / "inv.xlsx"
    p.write_text("")
    with pytest.raises(InventoryError):
        load_inventory(p)
