"""Tests for the NetBox client write path with a mocked httpx transport."""

import json

import httpx
import pytest

from netbox_mcp.client import NetboxClient, NetboxError


def client_with(handler, host_header=""):
    return NetboxClient(
        "https://netbox.example",
        "nbt_abc.xyz",
        transport=httpx.MockTransport(handler),
        host_header=host_header,
    )


@pytest.mark.asyncio
async def test_create_posts_json_body():
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["body"] = request.content.decode()
        return httpx.Response(201, json={"id": 1, "name": "pi-durable"})

    c = client_with(handler)
    try:
        out = await c.create("virtualization/virtual-machines", {"name": "pi-durable"})
    finally:
        await c.aclose()
    assert seen["method"] == "POST"
    assert seen["url"].endswith("/api/virtualization/virtual-machines/")
    assert json.loads(seen["body"]) == {"name": "pi-durable"}
    assert out["id"] == 1


@pytest.mark.asyncio
async def test_update_patches_with_id():
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"id": 11, "vcpus": 4})

    c = client_with(handler)
    try:
        out = await c.update("virtualization/virtual-machines", 11, {"vcpus": 4})
    finally:
        await c.aclose()
    assert seen["method"] == "PATCH"
    assert seen["url"].endswith("/api/virtualization/virtual-machines/11/")
    assert out["vcpus"] == 4


@pytest.mark.asyncio
async def test_delete_returns_empty_on_204():
    seen = {}

    def handler(request):
        seen["method"] = request.method
        return httpx.Response(204)

    c = client_with(handler)
    try:
        out = await c.delete("dcim/devices", 5)
    finally:
        await c.aclose()
    assert seen["method"] == "DELETE"
    assert out == {}


@pytest.mark.asyncio
async def test_write_error_raises():
    def handler(request):
        return httpx.Response(400, text="bad request")

    c = client_with(handler)
    try:
        with pytest.raises(NetboxError):
            await c.create("ipam/prefixes", {"prefix": "192.168.9.0/24"})
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_host_header_override():
    seen = {}

    def handler(request):
        seen["host"] = request.headers.get("host")
        return httpx.Response(200, json={"count": 0, "results": []})

    c = client_with(handler, host_header="netbox.apps.stdout.pt")
    try:
        await c.sites()
    finally:
        await c.aclose()
    assert seen["host"] == "netbox.apps.stdout.pt"


@pytest.mark.asyncio
async def test_resolve_id_returns_none_when_missing():
    def handler(request):
        return httpx.Response(200, json={"count": 0, "results": []})

    c = client_with(handler)
    try:
        assert await c.resolve_id("virtualization/clusters", {"name": "nope"}) is None
    finally:
        await c.aclose()
