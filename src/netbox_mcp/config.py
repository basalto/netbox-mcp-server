"""Configuration management for the NetBox MCP Server using Pydantic Settings."""

from basalto_mcp import MCPBaseSettings
from pydantic import Field


class Settings(MCPBaseSettings):
    """Application settings loaded from environment variables and .env file.

    Inherits ``.env`` loading, case-insensitivity, and the optional
    ``mcp_auth_token`` (``MCP_AUTH_TOKEN``) from :class:`MCPBaseSettings`.
    """

    netbox_url: str = Field(
        default="https://netbox.apps.stdout.pt",
        description="NetBox base URL (scheme://host:port, no trailing slash)",
        validation_alias="NETBOX_URL",
    )

    netbox_token: str = Field(
        default="",
        description="NetBox API token (V2 bearer, form nbt_<key>.<plaintext>)",
        validation_alias="NETBOX_TOKEN",
    )

    verify_ssl: bool = Field(
        default=True,
        description="Verify the TLS certificate of the NetBox API (set false for self-signed)",
        validation_alias="NETBOX_VERIFY_SSL",
    )

    request_timeout: float = Field(
        default=15.0,
        description="HTTP request timeout in seconds",
        validation_alias="NETBOX_REQUEST_TIMEOUT",
    )

    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR)",
        validation_alias="NETBOX_LOG_LEVEL",
    )

    allow_write: bool = Field(
        default=False,
        description=(
            "Enable the create/update/delete tools. Read tools always work; "
            "write tools refuse with a clear error unless this is true."
        ),
        validation_alias="NETBOX_ALLOW_WRITE",
    )

    host_header: str = Field(
        default="",
        description=(
            "Optional Host header to send instead of the URL's host. Needed when "
            "NETBOX_URL is the in-cluster service name (e.g. "
            "http://netbox.netbox.svc.cluster.local) but Django ALLOWED_HOSTS only "
            "accepts the public FQDN."
        ),
        validation_alias="NETBOX_HOST_HEADER",
    )
