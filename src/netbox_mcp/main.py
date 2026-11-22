"""Main entry point for the NetBox MCP Server.

Read tools are always available. Write tools (create/update/delete) are gated
behind ``NETBOX_ALLOW_WRITE=true`` so the server stays read-only unless the
operator explicitly enables mutation.
"""

from __future__ import annotations

import importlib.metadata
from typing import Any

from basalto_mcp import make_auth, serve
from fastmcp import FastMCP

from .client import NetboxClient, NetboxError
from .config import Settings

settings = Settings()

_auth_provider = make_auth(settings, client_id="netbox-mcp-server")
mcp = FastMCP("NetBox MCP Server", auth=_auth_provider)

if _auth_provider is not None:
    print("MCP bearer-token authentication enabled")
else:
    print("WARNING: MCP auth is DISABLED (MCP_AUTH_TOKEN not set) - server is unauthenticated")


async def _client() -> NetboxClient:
    """Create a NetBox client, raising a clean error when the token is missing."""
    if not settings.netbox_token:
        raise NetboxError(
            "NETBOX_TOKEN is not configured. Set it in .env (V2 bearer token nbt_...)."
        )
    return NetboxClient(
        settings.netbox_url,
        settings.netbox_token,
        timeout=settings.request_timeout,
        verify=settings.verify_ssl,
        host_header=settings.host_header,
    )


def _require_write() -> None:
    """Raise unless NETBOX_ALLOW_WRITE is enabled."""
    if not settings.allow_write:
        raise NetboxError(
            "Write is disabled: set NETBOX_ALLOW_WRITE=true to use create/update/delete tools."
        )


async def _resolve(client: NetboxClient, endpoint: str, params: dict[str, Any]) -> int:
    """Resolve an object id by lookup params, raising a clean error if missing."""
    obj_id = await client.resolve_id(endpoint, params)
    if obj_id is None:
        raise NetboxError(f"no {endpoint} matches {params}")
    return obj_id


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Health check to verify the server is running and can reach NetBox.

    Returns:
        Status information plus NetBox connectivity.
    """
    try:
        client = await _client()
    except NetboxError as exc:
        return {
            "status": "unhealthy",
            "error": str(exc),
            "version": importlib.metadata.version("netbox-mcp-server"),
        }
    try:
        await client.sites()
        netbox_reachable = "ok"
    except NetboxError as exc:
        netbox_reachable = f"error: {exc}"
    finally:
        await client.aclose()
    return {
        "status": "healthy" if netbox_reachable == "ok" else "unhealthy",
        "netbox_reachable": netbox_reachable,
        "netbox_url": settings.netbox_url,
        "write_enabled": settings.allow_write,
        "version": importlib.metadata.version("netbox-mcp-server"),
    }


# ---------------------------------------------------------------------------
# DCIM
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_sites() -> dict[str, Any]:
    """List NetBox sites (e.g. Home, Benedita).

    Returns:
        Each site's name, slug, status, and facility.
    """
    client = await _client()
    try:
        return await client.sites()
    finally:
        await client.aclose()


@mcp.tool()
async def list_devices(name: str = "", site: str = "", role: str = "") -> dict[str, Any]:
    """List physical devices in NetBox.

    Args:
        name: optional case-insensitive substring filter on device name.
        site: optional site slug filter (e.g. "home", "benedita").
        role: optional role slug filter (e.g. "hypervisor", "storage", "gateway").

    Returns:
        ``results``: each device's name, role, status, site, primary IP.
    """
    client = await _client()
    try:
        return await client.devices(name=name or None, site=site or None, role=role or None)
    finally:
        await client.aclose()


@mcp.tool()
async def get_device(name: str) -> dict[str, Any]:
    """Get one physical device by exact name.

    Args:
        name: exact device name (e.g. "server1", "nas3", "uxg-pro").

    Returns:
        The device object, or ``{"found": false}``.
    """
    client = await _client()
    try:
        device = await client.get_device(name)
        return device if device else {"found": False, "name": name}
    finally:
        await client.aclose()


@mcp.tool()
async def list_interfaces(device: str = "") -> dict[str, Any]:
    """List physical device interfaces (dcim.interfaces).

    Args:
        device: optional device name filter.

    Returns:
        ``results``: interface name, type, enabled, and assigned IP.
    """
    client = await _client()
    try:
        return await client.interfaces(device=device or None)
    finally:
        await client.aclose()


@mcp.tool()
async def list_device_roles() -> dict[str, Any]:
    """List device roles (Hypervisor, Storage, Gateway, Switch, AP, Desktop, ...).

    Returns:
        Role name, slug, and count of devices in each role.
    """
    client = await _client()
    try:
        return await client.device_roles()
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Virtualization
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_virtual_machines(name: str = "") -> dict[str, Any]:
    """List virtual machines in NetBox.

    Args:
        name: optional case-insensitive substring filter.

    Returns:
        ``results``: each VM's name, cluster, vcpus, memory, status, primary IP.
    """
    client = await _client()
    try:
        return await client.virtual_machines(name=name or None)
    finally:
        await client.aclose()


@mcp.tool()
async def get_virtual_machine(name: str) -> dict[str, Any]:
    """Get one virtual machine by exact name.

    Args:
        name: exact VM name (e.g. "k3s-4", "ubuntu-docker").

    Returns:
        The VM object, or ``{"found": false}``.
    """
    client = await _client()
    try:
        vm = await client.get_virtual_machine(name)
        return vm if vm else {"found": False, "name": name}
    finally:
        await client.aclose()


@mcp.tool()
async def list_clusters() -> dict[str, Any]:
    """List virtualization clusters.

    Returns:
        Cluster name, type, and member count.
    """
    client = await _client()
    try:
        return await client.clusters()
    finally:
        await client.aclose()


@mcp.tool()
async def list_vm_interfaces(vm: str = "") -> dict[str, Any]:
    """List VM interfaces (virtualization.interfaces).

    Args:
        vm: optional VM name filter.

    Returns:
        ``results``: interface name and assigned IP.
    """
    client = await _client()
    try:
        return await client.vm_interfaces(vm=vm or None)
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# IPAM
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_prefixes(prefix: str = "") -> dict[str, Any]:
    """List IP prefixes (subnets).

    Args:
        prefix: optional exact prefix filter (e.g. "192.168.1.0/24").

    Returns:
        ``results``: prefix, VLAN, description, and utilization.
    """
    client = await _client()
    try:
        return await client.prefixes(prefix=prefix or None)
    finally:
        await client.aclose()


@mcp.tool()
async def list_vlans() -> dict[str, Any]:
    """List VLANs.

    Returns:
        Each VLAN's vid, name, and site.
    """
    client = await _client()
    try:
        return await client.vlans()
    finally:
        await client.aclose()


@mcp.tool()
async def list_ip_addresses(address: str = "", family: int = 0) -> dict[str, Any]:
    """List IP addresses.

    Args:
        address: optional exact address filter (e.g. "192.168.1.134/24").
        family: optional address family (4 or 6).

    Returns:
        ``results``: each IP's address, family, status, and assigned object.
    """
    client = await _client()
    try:
        return await client.ip_addresses(address=address or None, family=family or None)
    finally:
        await client.aclose()


@mcp.tool()
async def list_vrfs() -> dict[str, Any]:
    """List VRFs (used to model overlapping RFC1918 space across sites).

    Returns:
        VRF name and route-distinguisher.
    """
    client = await _client()
    try:
        return await client.vrfs()
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Write tools (gated behind NETBOX_ALLOW_WRITE)
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_virtual_machine(
    name: str,
    cluster: str | int = 1,
    vcpus: float = 0,
    memory: int = 0,
    status: str = "active",
    comments: str = "",
) -> dict[str, Any]:
    """Create a virtual machine (write — requires NETBOX_ALLOW_WRITE).

    Args:
        name: VM name (must not already exist).
        cluster: cluster id or name (default 1 = the homelab "proxmox" cluster).
        vcpus: number of vCPUs (0 = leave unset).
        memory: memory in MB (0 = leave unset).
        status: active / offline / planned / staged / failed / decommissioning.
        comments: free-text note.

    Returns:
        The created VM object.
    """
    _require_write()
    client = await _client()
    try:
        data: dict[str, Any] = {"name": name, "status": status}
        if isinstance(cluster, str):
            data["cluster"] = await _resolve(client, "virtualization/clusters", {"name": cluster})
        else:
            data["cluster"] = cluster
        if vcpus:
            data["vcpus"] = vcpus
        if memory:
            data["memory"] = memory
        if comments:
            data["comments"] = comments
        return await client.create("virtualization/virtual-machines", data)
    finally:
        await client.aclose()


@mcp.tool()
async def update_virtual_machine(
    name: str,
    vcpus: float | None = None,
    memory: int | None = None,
    status: str | None = None,
    primary_ip4: str | None = None,
    comments: str | None = None,
) -> dict[str, Any]:
    """Update an existing virtual machine by name (write).

    Only the fields you pass are changed; pass None to leave a field untouched.

    Args:
        name: existing VM name.
        vcpus: new vCPU count.
        memory: new memory in MB.
        status: new status value.
        primary_ip4: IP id (or address string) to set as the primary IPv4.
        comments: new comment text.

    Returns:
        The updated VM object.
    """
    _require_write()
    client = await _client()
    try:
        vm_id = await _resolve(client, "virtualization/virtual-machines", {"name": name})
        data: dict[str, Any] = {}
        if vcpus is not None:
            data["vcpus"] = vcpus
        if memory is not None:
            data["memory"] = memory
        if status is not None:
            data["status"] = status
        if comments is not None:
            data["comments"] = comments
        if primary_ip4 is not None:
            if str(primary_ip4).isdigit():
                data["primary_ip4"] = int(primary_ip4)
            else:
                ip_id = await _resolve(client, "ipam/ip-addresses", {"address": primary_ip4})
                data["primary_ip4"] = ip_id
        return await client.update("virtualization/virtual-machines", vm_id, data)
    finally:
        await client.aclose()


@mcp.tool()
async def delete_virtual_machine(name: str) -> dict[str, Any]:
    """Delete a virtual machine by name (write).

    Deleting the VM also deletes its interfaces and any IPs assigned to them
    (cascade). No separate IP cleanup is needed.

    Args:
        name: VM name.

    Returns:
        {"deleted": true, "id": <vm id>}.
    """
    _require_write()
    client = await _client()
    try:
        vm_id = await _resolve(client, "virtualization/virtual-machines", {"name": name})
        await client.delete("virtualization/virtual-machines", vm_id)
        return {"deleted": True, "id": vm_id}
    finally:
        await client.aclose()


@mcp.tool()
async def create_vm_interface(
    vm: str,
    name: str = "eth0",
    mac_address: str = "",
) -> dict[str, Any]:
    """Create an interface on a virtual machine (write).

    Args:
        vm: VM name (must exist).
        name: interface name (default "eth0").
        mac_address: optional MAC address (AA:BB:CC:DD:EE:FF).

    Returns:
        The created interface object.
    """
    _require_write()
    client = await _client()
    try:
        vm_id = await _resolve(client, "virtualization/virtual-machines", {"name": vm})
        data: dict[str, Any] = {"virtual_machine": vm_id, "name": name}
        if mac_address:
            data["mac_address"] = mac_address
        return await client.create("virtualization/interfaces", data)
    finally:
        await client.aclose()


@mcp.tool()
async def create_ip_address(
    address: str,
    dns_name: str = "",
    status: str = "active",
    assigned_object_type: str = "",
    assigned_object_id: int = 0,
    description: str = "",
) -> dict[str, Any]:
    """Create an IP address (write).

    Args:
        address: IP in CIDR form (e.g. "192.168.1.29/24").
        dns_name: optional reverse-DNS name.
        status: active / reserved / deprecated / dhcp / slaac.
        assigned_object_type: one of "virtualization.vminterface",
            "dcim.interface", "ipam.fhrpgroup" (leave empty for no assignment).
        assigned_object_id: id of the interface to assign to (0 = unassigned).
        description: free-text note.

    Returns:
        The created IP object.
    """
    _require_write()
    client = await _client()
    try:
        data: dict[str, Any] = {"address": address, "status": status}
        if dns_name:
            data["dns_name"] = dns_name
        if description:
            data["description"] = description
        if assigned_object_type and assigned_object_id:
            data["assigned_object_type"] = assigned_object_type
            data["assigned_object_id"] = assigned_object_id
        return await client.create("ipam/ip-addresses", data)
    finally:
        await client.aclose()


@mcp.tool()
async def delete_ip_address(address: str) -> dict[str, Any]:
    """Delete an IP address (write).

    Args:
        address: exact address (e.g. "192.168.1.29/24").

    Returns:
        {"deleted": true, "id": <ip id>}.
    """
    _require_write()
    client = await _client()
    try:
        ip_id = await _resolve(client, "ipam/ip-addresses", {"address": address})
        await client.delete("ipam/ip-addresses", ip_id)
        return {"deleted": True, "id": ip_id}
    finally:
        await client.aclose()


@mcp.tool()
async def create_device(
    name: str,
    role: str = "",
    device_type: str = "",
    site: str = "",
    status: str = "active",
) -> dict[str, Any]:
    """Create a physical device (write).

    Args:
        name: device name (must not already exist).
        role: role slug (e.g. "hypervisor", "storage", "gateway", "switch",
            "access-point", "desktop").
        device_type: device-type model name to look up (optional).
        site: site slug (e.g. "home").
        status: active / offline / planned / staged / failed / inventory / decommissioning.

    Returns:
        The created device object.
    """
    _require_write()
    client = await _client()
    try:
        data: dict[str, Any] = {"name": name, "status": status}
        if role:
            data["role"] = await _resolve(client, "dcim/device-roles", {"slug": role})
        if device_type:
            data["device_type"] = await _resolve(
                client, "dcim/device-types", {"model": device_type}
            )
        if site:
            data["site"] = await _resolve(client, "dcim/sites", {"slug": site})
        return await client.create("dcim/devices", data)
    finally:
        await client.aclose()


@mcp.tool()
async def delete_device(name: str) -> dict[str, Any]:
    """Delete a physical device by name (write).

    Args:
        name: device name.

    Returns:
        {"deleted": true, "id": <device id>}.
    """
    _require_write()
    client = await _client()
    try:
        device_id = await _resolve(client, "dcim/devices", {"name": name})
        await client.delete("dcim/devices", device_id)
        return {"deleted": True, "id": device_id}
    finally:
        await client.aclose()


@mcp.tool()
async def create_prefix(
    prefix: str,
    status: str = "active",
    site: str = "",
    vlan: int = 0,
    description: str = "",
) -> dict[str, Any]:
    """Create an IP prefix (write).

    Args:
        prefix: prefix in CIDR form (e.g. "192.168.1.0/24").
        status: active / reserved / deprecated / container.
        site: site slug (optional).
        vlan: VLAN id to associate (optional).
        description: free-text note.

    Returns:
        The created prefix object.
    """
    _require_write()
    client = await _client()
    try:
        data: dict[str, Any] = {"prefix": prefix, "status": status}
        if site:
            data["site"] = await _resolve(client, "dcim/sites", {"slug": site})
        if vlan:
            data["vlan"] = await _resolve(client, "ipam/vlans", {"vid": vlan})
        if description:
            data["description"] = description
        return await client.create("ipam/prefixes", data)
    finally:
        await client.aclose()


@mcp.tool()
async def create_vlan(
    vid: int,
    name: str,
    site: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Create a VLAN (write).

    Args:
        vid: VLAN id (1-4094).
        name: VLAN name.
        site: site slug (optional).
        description: free-text note.

    Returns:
        The created VLAN object.
    """
    _require_write()
    client = await _client()
    try:
        data: dict[str, Any] = {"vid": vid, "name": name}
        if site:
            data["site"] = await _resolve(client, "dcim/sites", {"slug": site})
        if description:
            data["description"] = description
        return await client.create("ipam/vlans", data)
    finally:
        await client.aclose()


@mcp.tool()
async def provision_vm(
    name: str,
    ip: str,
    mac: str = "",
    dns_name: str = "",
    cluster: str | int = 1,
    vcpus: float = 2,
    memory: int = 2048,
    comments: str = "",
) -> dict[str, Any]:
    """Idempotently create/update a VM with an eth0 interface, an IP, and primary_ip4.

    Get-or-create semantics (this is the seed.py replacement for the common
    VM/LXC case): the VM is created if missing and its vcpus/memory updated
    otherwise; the eth0 interface and the given IP are created only if absent;
    primary_ip4 is set if not already.

    Args:
        name: VM name.
        ip: IP in CIDR form (e.g. "192.168.1.29/24").
        mac: optional MAC address for eth0.
        dns_name: optional reverse-DNS name for the IP (default "").
        cluster: cluster id or name (default 1).
        vcpus: vCPU count.
        memory: memory in MB.
        comments: free-text note for the VM.

    Returns:
        {"vm_id", "interface_id", "ip_id", "created": bool}.
    """
    _require_write()
    client = await _client()
    try:
        vm = await client.get_virtual_machine(name)
        created = vm is None
        if vm is None:
            data: dict[str, Any] = {
                "name": name,
                "status": "active",
                "vcpus": vcpus,
                "memory": memory,
            }
            if isinstance(cluster, str):
                data["cluster"] = await _resolve(
                    client, "virtualization/clusters", {"name": cluster}
                )
            else:
                data["cluster"] = cluster
            if comments:
                data["comments"] = comments
            vm = await client.create("virtualization/virtual-machines", data)
        vm_id = vm["id"]

        iface = await client.get_first(
            "virtualization/interfaces", {"virtual_machine_id": vm_id, "name": "eth0"}
        )
        if iface is None:
            idata: dict[str, Any] = {"virtual_machine": vm_id, "name": "eth0"}
            if mac:
                idata["mac_address"] = mac
            iface = await client.create("virtualization/interfaces", idata)

        ipobj = await client.get_first("ipam/ip-addresses", {"address": ip})
        if ipobj is None:
            ipobj = await client.create(
                "ipam/ip-addresses",
                {
                    "address": ip,
                    "status": "active",
                    "dns_name": dns_name,
                    "assigned_object_type": "virtualization.vminterface",
                    "assigned_object_id": iface["id"],
                },
            )

        if not vm.get("primary_ip4"):
            vm = await client.update(
                "virtualization/virtual-machines", vm_id, {"primary_ip4": ipobj["id"]}
            )

        return {
            "vm_id": vm_id,
            "interface_id": iface["id"],
            "ip_id": ipobj["id"],
            "created": created,
        }
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the MCP server."""
    print(f"NetBox URL: {settings.netbox_url}")
    serve(mcp, default_port=3102)


if __name__ == "__main__":
    main()
