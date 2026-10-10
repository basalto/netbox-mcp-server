"""Configuration management for the NetBox MCP Server using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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

    mcp_auth_token: str | None = Field(
        default=None,
        description="Optional bearer token required on HTTP transports",
        validation_alias="MCP_AUTH_TOKEN",
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
