"""Optional: collect servers from a live Azure subscription.

Requires the ``azure`` extra (``pip install "azmigrate-check[azure]"``) and a
credential that ``DefaultAzureCredential`` can find, e.g. ``az login`` (Azure CLI),
environment variables, or a managed identity. Access is read-only; the account
needs at least the *Reader* role on the subscription.

Backup status is not read from Recovery Services vaults in this release, so
live-scanned VMs report backup as *unknown*.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from azmigrate_check.models import Server


class AzureUnavailableError(RuntimeError):
    """Raised when the Azure SDK is missing or authentication/listing fails."""


def _parse_id(resource_id: str) -> tuple[str, str]:
    """Return (resource_group, name) from an ARM resource ID."""
    parts = resource_id.strip("/").split("/")
    lower = [p.lower() for p in parts]
    rg = parts[lower.index("resourcegroups") + 1] if "resourcegroups" in lower else ""
    return rg, parts[-1]


def _clean(text: str | None) -> str:
    return (text or "").replace("_", ".").replace("-", " ").strip()


def _os_from_vm(vm: Any, instance_view: Any | None) -> tuple[str, str]:
    if instance_view is not None and getattr(instance_view, "os_name", None):
        return instance_view.os_name, getattr(instance_view, "os_version", "") or ""
    storage = getattr(vm, "storage_profile", None)
    image = getattr(storage, "image_reference", None)
    if image is not None and getattr(image, "offer", None):
        return _clean(image.offer), _clean(getattr(image, "sku", ""))
    os_disk = getattr(storage, "os_disk", None)
    os_type = getattr(os_disk, "os_type", None)
    return (str(getattr(os_type, "value", os_type)) if os_type else ""), ""


def _largest_disk_gb(vm: Any) -> float | None:
    storage = getattr(vm, "storage_profile", None)
    if storage is None:
        return None
    sizes = []
    os_disk = getattr(storage, "os_disk", None)
    if os_disk is not None and getattr(os_disk, "disk_size_gb", None):
        sizes.append(os_disk.disk_size_gb)
    for d in getattr(storage, "data_disks", None) or []:
        if getattr(d, "disk_size_gb", None):
            sizes.append(d.disk_size_gb)
    return float(max(sizes)) if sizes else None


def _public_ips(vm: Any, network_client: Any) -> list[str]:
    ips: list[str] = []
    profile = getattr(vm, "network_profile", None)
    for nic_ref in getattr(profile, "network_interfaces", None) or []:
        rg, nic_name = _parse_id(nic_ref.id)
        nic = network_client.network_interfaces.get(rg, nic_name)
        for cfg in getattr(nic, "ip_configurations", None) or []:
            pip_ref = getattr(cfg, "public_ip_address", None)
            if pip_ref is None or not getattr(pip_ref, "id", None):
                continue
            pip_rg, pip_name = _parse_id(pip_ref.id)
            pip = network_client.public_ip_addresses.get(pip_rg, pip_name)
            ips.append(getattr(pip, "ip_address", None) or pip_name)
    return ips


def collect_servers(compute_client: Any, network_client: Any | None = None) -> list[Server]:
    """Build Server records from Azure SDK clients (duck-typed for testability)."""
    size_cache: dict[str, dict[str, Any]] = {}
    servers: list[Server] = []
    for vm in compute_client.virtual_machines.list_all():
        rg, _ = _parse_id(vm.id)
        location = vm.location
        if location not in size_cache:
            size_cache[location] = {
                s.name.lower(): s for s in compute_client.virtual_machine_sizes.list(location)
            }
        vm_size = str(getattr(vm.hardware_profile, "vm_size", "") or "")
        size = size_cache[location].get(vm_size.lower())

        try:
            iv = compute_client.virtual_machines.instance_view(rg, vm.name)
        except Exception:
            iv = None
        os_name, os_version = _os_from_vm(vm, iv)

        public_ips = _public_ips(vm, network_client) if network_client is not None else []
        tags = {str(k).lower(): str(v) for k, v in (vm.tags or {}).items()}
        servers.append(
            Server(
                name=vm.name,
                os=os_name,
                os_version=os_version,
                cpu=getattr(size, "number_of_cores", None),
                ram_gb=(size.memory_in_mb / 1024) if size is not None else None,
                disk_gb=_largest_disk_gb(vm),
                public_ip=", ".join(public_ips),
                tags=tags,
                backup=None,
                environment=tags.get("environment", tags.get("env", "")),
                source="azure",
            )
        )
    return servers


def load_from_subscription(subscription_id: str | None = None) -> list[Server]:
    """Authenticate with DefaultAzureCredential and list all VMs in a subscription."""
    subscription_id = subscription_id or os.environ.get("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        raise AzureUnavailableError(
            "No subscription ID given. Pass --subscription or set AZURE_SUBSCRIPTION_ID."
        )
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.compute import ComputeManagementClient
        from azure.mgmt.network import NetworkManagementClient
    except ImportError as exc:
        raise AzureUnavailableError(
            'Azure SDK not installed. Install with: pip install "azmigrate-check[azure]"'
        ) from exc

    # The SDK logs verbose credential-chain diagnostics; we report a concise error instead.
    logging.getLogger("azure").setLevel(logging.ERROR)
    try:
        credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        compute = ComputeManagementClient(credential, subscription_id)
        network = NetworkManagementClient(credential, subscription_id)
        return collect_servers(compute, network)
    except Exception as exc:
        raise AzureUnavailableError(
            f"Could not read subscription {subscription_id}: {type(exc).__name__}: "
            f"{str(exc).splitlines()[0] if str(exc) else ''} "
            "Check that you are signed in (az login) and have Reader access."
        ) from exc
