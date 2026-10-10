# netbox-mcp-server

Read-only MCP server for the homelab NetBox DCIM/IPAM API — the source of truth
for hosts, VMs, IPs, prefixes, VLANs, sites, and clusters. Agents query it
instead of reading hardcoded prose, so "what exists" can't drift.

Read-only by design (matching the other homelab MCP servers): every tool is a
GET. No write path, no ALLOW_WRITE flag.

## Config (.env)

| Var | Default | Meaning |
|---|---|---|
| `NETBOX_URL` | `https://netbox.apps.stdout.pt` | NetBox base URL |
| `NETBOX_TOKEN` | — | V2 bearer token `nbt_<key>.<plaintext>` |
| `MCP_AUTH_TOKEN` | empty | Optional bearer token on the MCP endpoint |
| `NETBOX_VERIFY_SSL` | `true` | Verify the LE cert (leave true) |
| `NETBOX_REQUEST_TIMEOUT` | `15` | HTTP timeout (s) |
| `NETBOX_LOG_LEVEL` | `INFO` | Log level |

Minting a token (in the NetBox pod):

    Token.objects.create(user=u, version=TokenVersionChoices.V2)
    auth header = t.get_auth_header_prefix() + t._token

## Run

    # stdio (local / MCP client)
    FASTMCP_TRANSPORT=stdio netbox-mcp-server

    # streamable-http (k3s deployment)
    FASTMCP_TRANSPORT=streamable-http FASTMCP_PORT=3102 netbox-mcp-server

## Tools

`health_check`, `list_sites`, `list_devices`, `get_device`, `list_interfaces`,
`list_device_roles`, `list_virtual_machines`, `get_virtual_machine`,
`list_clusters`, `list_vm_interfaces`, `list_prefixes`, `list_vlans`,
`list_ip_addresses`, `list_vrfs`.
