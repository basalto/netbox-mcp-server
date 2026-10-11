"""Tests for config loading and static-token auth."""

import pytest
from basalto_mcp import StaticTokenAuth

from netbox_mcp.config import Settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("NETBOX_URL", raising=False)
    monkeypatch.delenv("NETBOX_TOKEN", raising=False)
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    s = Settings(_env_file=None)
    assert s.netbox_url == "https://netbox.apps.stdout.pt"
    assert s.netbox_token == ""
    assert s.verify_ssl is True
    assert s.mcp_auth_token is None


def test_settings_env(monkeypatch):
    monkeypatch.setenv("NETBOX_URL", "http://netbox.example")
    monkeypatch.setenv("NETBOX_TOKEN", "nbt_abc.xyz")
    monkeypatch.setenv("MCP_AUTH_TOKEN", "secret")
    s = Settings(_env_file=None)
    assert s.netbox_url == "http://netbox.example"
    assert s.netbox_token == "nbt_abc.xyz"
    assert s.mcp_auth_token == "secret"


@pytest.mark.asyncio
async def test_auth_accepts_correct_token():
    a = StaticTokenAuth("secret", client_id="netbox-mcp-server")
    tok = await a.verify_token("secret")
    assert tok is not None
    assert tok.client_id == "netbox-mcp-server"


@pytest.mark.asyncio
async def test_auth_rejects_wrong_token():
    a = StaticTokenAuth("secret")
    assert await a.verify_token("wrong") is None
    assert await a.verify_token("") is None


def test_auth_requires_nonempty_token():
    with pytest.raises(ValueError):
        StaticTokenAuth("")
