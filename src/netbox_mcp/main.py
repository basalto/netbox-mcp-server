"""Main entry point for the NetBox MCP Server.

Read-only by design (matching the other homelab MCP servers): every tool is a
GET against the NetBox API. There is no write path and no ALLOW_WRITE flag.
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
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@mcp.tool()
async def health_check() -> dict[str, str]:
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
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the MCP server."""
    print(f"NetBox URL: {settings.netbox_url}")
    serve(mcp, default_port=3102)


if __name__ == "__main__":
    main()
