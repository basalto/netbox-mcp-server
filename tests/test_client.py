"""Tests for the NetBox client with a mocked httpx transport."""

import httpx
import pytest

from netbox_mcp.client import NetboxClient, NetboxError


def client_with(handler):
    return NetboxClient(
        "https://netbox.example",
        "nbt_abc.xyz",
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_list_sends_auth_and_limit():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"count": 1, "results": [{"id": 1}]})

    c = client_with(handler)
    try:
        data = await c.sites()
    finally:
        await c.aclose()
    assert "netbox.example/api/dcim/sites/" in seen["url"]
    assert seen["auth"] == "Token nbt_abc.xyz"
    assert data["count"] == 1


@pytest.mark.asyncio
async def test_error_raises():
    def handler(request):
        return httpx.Response(403, text="Forbidden")

    c = client_with(handler)
    try:
        with pytest.raises(NetboxError):
            await c.sites()
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_get_device_returns_none_when_missing():
    def handler(request):
        return httpx.Response(200, json={"count": 0, "results": []})

    c = client_with(handler)
    try:
        assert await c.get_device("nope") is None
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_list_without_token_omits_auth_header():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"count": 0, "results": []})

    c = NetboxClient("https://netbox.example", "", transport=httpx.MockTransport(handler))
    try:
        await c.sites()
    finally:
        await c.aclose()
    assert seen["auth"] is None
