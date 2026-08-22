import pytest
from pydantic import ValidationError

from pcradio_mcp.config import Settings


def test_settings_normalize_base_url_and_accept_stdio():
    settings = Settings(
        pcradio_base_url="https://radio.example/", mcp_transport="stdio",
    )
    assert settings.pcradio_base_url == "https://radio.example"
    assert settings.mcp_transport == "stdio"


@pytest.mark.parametrize("values, message", [
    ({"pcradio_base_url": "ftp://radio"}, "http or https"),
    ({"mcp_transport": "sse"}, "stdio or streamable-http"),
])
def test_invalid_settings(values, message):
    with pytest.raises(ValidationError, match=message):
        Settings(**values)
