"""Async HTTP client for the NetBox REST API.

NetBox authenticates with a token carried in the ``Authorization`` header::

    Authorization: Token <token>

Tokens are V2 bearer tokens of the form ``nbt_<key>.<plaintext>`` (minted in
the NetBox pod; the chart's ``superuser.apiToken`` does NOT create one).

The API is standard Django-REST: list endpoints return
``{"count", "next", "previous", "results"}`` and ``?limit=0`` returns every
result in a single page (no follow-the-next-link loop needed).

All methods return the parsed JSON payload as a dict. API errors raise
``NetboxError``.
"""

from __future__ import annotations

from typing import Any

import httpx


class NetboxError(RuntimeError):
    """Raised when the NetBox API returns an error or unexpected payload."""


class NetboxClient:
    """Authenticated async client for the NetBox REST API."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 15.0,
        verify: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Token {token}"
        self._client = httpx.AsyncClient(
            timeout=timeout, verify=verify, headers=headers, transport=transport
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET one API endpoint and return the parsed JSON dict."""
        url = f"{self.base_url}/api/{endpoint}/"
        resp = await self._client.get(url, params=params)
        if resp.status_code >= 400:
            raise NetboxError(f"NetBox {endpoint} HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        if not isinstance(data, dict):
            raise NetboxError(f"NetBox {endpoint} returned a non-dict payload: {type(data).__name__}")
        return data

    async def list(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """List all objects of a type (limit=0, single page)."""
        merged = dict(params or {})
        merged.setdefault("limit", 0)
        return await self._request(endpoint, merged)

    async def get_first(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Return the first object matching params, or None."""
        data = await self.list(endpoint, params)
        results = data.get("results", [])
        return results[0] if results else None

    # ------------------------------------------------------------------
    # DCIM (sites, devices, interfaces, roles)
    # ------------------------------------------------------------------

    async def sites(self) -> dict[str, Any]:
        return await self.list("dcim/sites")

    async def devices(self, name: str | None = None, site: str | None = None, role: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if name:
            params["name__ic"] = name
        if site:
            params["site"] = site
        if role:
            params["role"] = role
        return await self.list("dcim/devices", params)

    async def get_device(self, name: str) -> dict[str, Any] | None:
        return await self.get_first("dcim/devices", {"name": name})

    async def interfaces(self, device: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if device:
            params["device"] = device
        return await self.list("dcim/interfaces", params)

    async def device_roles(self) -> dict[str, Any]:
        return await self.list("dcim/device-roles")

    # ------------------------------------------------------------------
    # Virtualization (VMs, clusters, VM interfaces)
    # ------------------------------------------------------------------

    async def virtual_machines(self, name: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if name:
            params["name__ic"] = name
        return await self.list("virtualization/virtual-machines", params)

    async def get_virtual_machine(self, name: str) -> dict[str, Any] | None:
        return await self.get_first("virtualization/virtual-machines", {"name": name})

    async def clusters(self) -> dict[str, Any]:
        return await self.list("virtualization/clusters")

    async def vm_interfaces(self, vm: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if vm:
            params["virtual_machine"] = vm
        return await self.list("virtualization/interfaces", params)

    # ------------------------------------------------------------------
    # IPAM (prefixes, VLANs, IPs, VRFs)
    # ------------------------------------------------------------------

    async def prefixes(self, prefix: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if prefix:
            params["prefix"] = prefix
        return await self.list("ipam/prefixes", params)

    async def vlans(self) -> dict[str, Any]:
        return await self.list("ipam/vlans")

    async def ip_addresses(self, address: str | None = None, family: int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if address:
            params["address"] = address
        if family:
            params["family"] = family
        return await self.list("ipam/ip-addresses", params)

    async def vrfs(self) -> dict[str, Any]:
        return await self.list("ipam/vrfs")
