from types import SimpleNamespace as NS

from azmigrate_check.azure_live import collect_servers

SUB = "/subscriptions/00000000-0000-0000-0000-000000000000"


class FakeVMs:
    def __init__(self, vms, views):
        self._vms, self._views = vms, views

    def list_all(self):
        return iter(self._vms)

    def instance_view(self, rg, name):
        if name not in self._views:
            raise RuntimeError("guest agent not reporting")
        return self._views[name]


def _vm(name, size, image=None, nics=(), tags=None, data_disks=()):
    return NS(
        id=f"{SUB}/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/{name}",
        name=name,
        location="westeurope",
        tags=tags,
        hardware_profile=NS(vm_size=size),
        storage_profile=NS(
            image_reference=image,
            os_disk=NS(disk_size_gb=128, os_type="Linux"),
            data_disks=[NS(disk_size_gb=d) for d in data_disks],
        ),
        network_profile=NS(network_interfaces=[NS(id=n) for n in nics]),
    )


def test_collect_servers_maps_sdk_objects():
    nic_id = f"{SUB}/resourceGroups/rg1/providers/Microsoft.Network/networkInterfaces/nic1"
    pip_id = f"{SUB}/resourceGroups/rg-net/providers/Microsoft.Network/publicIPAddresses/pip1"
    vms = [
        _vm(
            "vm1",
            "Standard_D4s_v5",
            image=NS(offer="WindowsServer", sku="2012-R2-Datacenter"),
            nics=[nic_id],
            tags={"Owner": "team"},
            data_disks=[1024],
        ),
        _vm(
            "vm2",
            "Standard_B2s",
            image=NS(offer="0001-com-ubuntu-server-jammy", sku="22_04-lts-gen2"),
        ),
    ]
    views = {"vm2": NS(os_name="ubuntu", os_version="22.04")}
    compute = NS(
        virtual_machines=FakeVMs(vms, views),
        virtual_machine_sizes=NS(
            list=lambda loc: [
                NS(name="Standard_D4s_v5", number_of_cores=4, memory_in_mb=16384),
                NS(name="Standard_B2s", number_of_cores=2, memory_in_mb=4096),
            ]
        ),
    )
    network = NS(
        network_interfaces=NS(
            get=lambda rg, n: NS(ip_configurations=[NS(public_ip_address=NS(id=pip_id))])
        ),
        public_ip_addresses=NS(
            get=lambda rg, n: NS(ip_address="203.0.113.9") if rg == "rg-net" else None
        ),
    )

    s1, s2 = collect_servers(compute, network)
    assert (s1.cpu, s1.ram_gb, s1.disk_gb) == (4, 16.0, 1024.0)
    assert s1.public_ip == "203.0.113.9"
    assert s1.tags == {"owner": "team"}
    assert "2012 R2" in s1.os_version
    assert s1.backup is None and s1.source == "azure"
    assert (s2.os, s2.os_version, s2.public_ip) == ("ubuntu", "22.04", "")
