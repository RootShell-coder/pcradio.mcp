from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pcradio_base_url: str = "http://pcradio.local"
    pcradio_timeout: float = Field(default=5.0, gt=0, le=60)
    mcp_transport: str = "streamable-http"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8080, ge=1, le=65535)
    mcp_bearer_token: SecretStr | None = None

    @field_validator("mcp_bearer_token", mode="before")
    @classmethod
    def empty_token_disables_authentication(cls, value):
        return None if value is None or not str(value).strip() else value

    @field_validator("pcradio_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("PCRADIO_BASE_URL must use http or https")
        return value

    @field_validator("mcp_transport")
    @classmethod
    def validate_transport(cls, value: str) -> str:
        if value not in {"stdio", "streamable-http"}:
            raise ValueError("MCP_TRANSPORT must be stdio or streamable-http")
        return value
