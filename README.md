# netbox-mcp-server

Read-only MCP server for the homelab NetBox DCIM/IPAM API — the source of truth
for hosts, VMs, IPs, prefixes, VLANs, sites, and clusters. Agents query it
instead of reading hardcoded prose, so "what exists" can't drift.

Write tools (create/update/delete for VMs, interfaces, IPs, devices, prefixes
and VLANs) are included but gated behind `NETBOX_ALLOW_WRITE=true`; read tools
always work. The `provision_vm` tool is the get-or-create seed.py replacement
for the common VM/LXC case.

## Config (.env)

| Var | Default | Meaning |
|---|---|---|
| `NETBOX_URL` | `https://netbox.apps.stdout.pt` | NetBox base URL |
| `NETBOX_TOKEN` | — | V2 bearer token `nbt_<key>.<plaintext>` |
| `MCP_AUTH_TOKEN` | empty | Optional bearer token on the MCP endpoint |
| `NETBOX_VERIFY_SSL` | `true` | Verify the LE cert (leave true) |
| `NETBOX_REQUEST_TIMEOUT` | `15` | HTTP timeout (s) |
| `NETBOX_LOG_LEVEL` | `INFO` | Log level |
| `NETBOX_ALLOW_WRITE` | `false` | Enable create/update/delete tools |
| `NETBOX_HOST_HEADER` | empty | Host header override (for the in-cluster service URL) |

Minting a token (in the NetBox pod — import from `users.choices`, NOT
`users.models`; the plaintext is the transient `t.token`):

    from users.models import Token
    from users.choices import TokenVersionChoices
    t = Token.objects.create(user=u, description="...", version=TokenVersionChoices.V2)
    print(t.get_auth_header_prefix() + t.token)   # "Bearer nbt_<key>.<plaintext>"

## Run

    # stdio (local / MCP client)
    FASTMCP_TRANSPORT=stdio netbox-mcp-server

    # streamable-http (k3s deployment)
    FASTMCP_TRANSPORT=streamable-http FASTMCP_PORT=3102 netbox-mcp-server

## Tools

Read: `health_check`, `list_sites`, `list_devices`, `get_device`,
`list_interfaces`, `list_device_roles`, `list_virtual_machines`,
`get_virtual_machine`, `list_clusters`, `list_vm_interfaces`, `list_prefixes`,
`list_vlans`, `list_ip_addresses`, `list_vrfs`.

Write (gated behind `NETBOX_ALLOW_WRITE=true`): `create_virtual_machine`,
`update_virtual_machine`, `delete_virtual_machine`, `create_vm_interface`,
`create_ip_address`, `delete_ip_address`, `create_device`, `delete_device`,
`create_prefix`, `create_vlan`, `provision_vm`.
